# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime
import time
from enum import Enum
from enum import auto
from functools import wraps
from itertools import chain
from typing import Any
from typing import Dict
from typing import Iterable
from typing import List
from typing import Optional
from uuid import uuid4

import pyarrow
from orso import DataFrame
from orso import converters

from opteryx import config
from opteryx import utils
from opteryx.exceptions import InvalidCursorStateError
from opteryx.exceptions import MissingSqlStatement
from opteryx.exceptions import UnsupportedSyntaxError
from opteryx.shared import QueryStatistics
from opteryx.shared.rolling_log import RollingLog
from opteryx.utils import sql

PROFILE_LOCATION = config.PROFILE_LOCATION


ROLLING_LOG = None
if PROFILE_LOCATION:
    ROLLING_LOG = RollingLog(PROFILE_LOCATION + ".log")


class CursorState(Enum):
    INITIALIZED = auto()
    EXECUTED = auto()
    CLOSED = auto()


def require_state(required_state):
    """
    Decorator to enforce a required state before a Cursor method is called.

    The decorator takes a required_state parameter which is the state the Cursor
    must be in before the decorated method can be called. If the state condition
    is not met, an InvalidCursorStateError is raised.

    Parameters:
        required_state: The state that the cursor must be in to execute the method.

    Returns:
        A wrapper function that checks the state and calls the original function.
    """

    def decorator(func):
        @wraps(func)
        def wrapper(obj, *args, **kwargs):
            if obj._state != required_state:
                raise InvalidCursorStateError(f"Cursor must be in {required_state} state.")
            return func(obj, *args, **kwargs)

        return wrapper

    return decorator


def transition_to(new_state):
    """
    Decorator to transition the Cursor to a new state after a method call.

    The decorator takes a new_state parameter which is the state the Cursor
    will transition to after the decorated method is called.

    Parameters:
        new_state: The new state to transition to after the method is called.

    Returns:
        A wrapper function that executes the original function and then updates the state.
    """

    def decorator(func):
        @wraps(func)
        def wrapper(obj, *args, **kwargs):
            # Execute the original method.
            result = func(obj, *args, **kwargs)
            # Transition to the new state.
            obj._state = new_state
            return result

        return wrapper

    return decorator


class Cursor(DataFrame):
    """
    This class inherits from the orso DataFrame library to provide features such as fetch.

    This class includes custom decorators @require_state and @transition_to for state management.
    """

    def __init__(self, connection):
        """
        Initializes the Cursor object, setting the initial state and binding the connection.

        Parameters:
            connection: Connection object
                The database connection object.
        """
        self.arraysize = 1
        self._connection = connection
        self._query_planner = None
        self._collected_stats = None
        self._plan = None
        self._qid = str(uuid4())
        self._statistics = QueryStatistics(self._qid)
        self._state = CursorState.INITIALIZED
        DataFrame.__init__(self, rows=[], schema=[])

    @property
    def id(self) -> str:
        """The unique internal reference for this query.

        Returns:
            The unique query identifier as a string.
        """
        return self._qid

    def _inner_execute(self, operation: str, params: Optional[Iterable] = None) -> Any:
        """
        Executes a single SQL operation within the current cursor.

        Parameters:
            operation: str
                SQL operation to be executed.
            params: Iterable, optional
                Parameters for the SQL operation, defaults to None.
        Returns:
            Results of the query execution.
        """

        from opteryx.components import query_planner

        if not operation:
            raise MissingSqlStatement("SQL provided was empty.")

        self._connection.context.history.append((operation, True, datetime.datetime.utcnow()))
        plans = query_planner(
            operation=operation, parameters=params, connection=self._connection, qid=self.id
        )

        try:
            first_item = next(plans)
        except RuntimeError:
            raise MissingSqlStatement(
                "SQL statement provided had no executable part, this may mean the statement was commented out."
            )

        plans = chain([first_item], plans)

        if ROLLING_LOG:
            ROLLING_LOG.append(operation)

        results = None
        for plan in plans:
            results = plan.execute()

        if results is not None:
            # we can't update tuples directly
            self._connection.context.history[-1] = tuple(
                True if i == 1 else value
                for i, value in enumerate(self._connection.context.history[-1])
            )
            return results

    def _execute_statements(self, operation, params: Optional[Iterable] = None):
        """
        Executes one or more SQL statements, properly handling comments, cleaning, and splitting.

        Parameters:
            operation: str
                SQL operation(s) to be executed.
            params: Iterable, optional
                Parameters for the SQL operation(s), defaults to None.

        Returns:
            Results of the query execution, if any.
        """
        statements = sql.remove_comments(operation)
        statements = sql.clean_statement(statements)
        statements = sql.split_sql_statements(statements)

        if len(statements) == 0:
            raise MissingSqlStatement("No statement found")

        if len(statements) > 1 and params is not None:
            raise UnsupportedSyntaxError("Batched queries cannot be parameterized.")

        results = None
        for index, statement in enumerate(statements):
            results = self._inner_execute(statement, params)
            if index < len(statements) - 1:
                for _ in results:
                    pass

        return results

    @require_state(CursorState.INITIALIZED)
    @transition_to(CursorState.EXECUTED)
    def execute(self, operation: str, params: Optional[Iterable] = None):
        """
        Executes the provided SQL operation, converting results to internal DataFrame format.

        Parameters:
            operation: str
                SQL operation to be executed.
            params: Iterable, optional
                Parameters for the SQL operation, defaults to None.
        """
        if hasattr(operation, "decode"):
            operation = operation.decode()
        results = self._execute_statements(operation, params)
        if results is not None:
            self._rows, self._schema = converters.from_arrow(results)
            self._cursor = iter(self._rows)

    @require_state(CursorState.INITIALIZED)
    @transition_to(CursorState.EXECUTED)
    def execute_to_arrow(
        self, operation: str, params: Optional[Iterable] = None, limit: Optional[int] = None
    ) -> pyarrow.Table:
        """
        Executes the SQL operation, bypassing conversion to Orso and returning directly in Arrow format.

        Parameters:
            operation: str
                SQL operation to be executed.
            params: Iterable, optional
                Parameters for the SQL operation, defaults to None.
            limit: int, optional
                Limit on the number of records to return, defaults to all records.

        Returns:
            The query results in Arrow table format.
        """
        results = self._execute_statements(operation, params)
        if results is not None:
            if limit is not None:
                results = utils.arrow.limit_records(results, limit)
        return pyarrow.concat_tables(results, promote=True)

    @property
    def stats(self) -> Dict[str, Any]:
        """
        Gets the execution statistics.

        Returns:
            Dictionary containing query execution statistics.
        """
        if self._statistics.end_time == 0:  # pragma: no cover
            self._statistics.end_time = time.time_ns()
        return self._statistics.as_dict()

    @property
    def messages(self) -> List[str]:
        """
        Gets the list of run-time warnings.

        Returns:
            List of warnings generated during query execution.
        """
        return self._statistics.messages

    @require_state(CursorState.EXECUTED)
    @transition_to(CursorState.CLOSED)
    def close(self):
        """
        Closes the cursor, releasing any resources and closing the associated connection.
        """
        self._connection.close()