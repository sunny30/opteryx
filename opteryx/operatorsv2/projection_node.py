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

"""
Projection Node

This is a SQL Query Execution Plan Node.

This Node eliminates columns that are not needed in a Relation. This is also the Node
that performs column renames.
"""

import pyarrow

from opteryx import EOS
from opteryx.managers.expression import NodeType
from opteryx.managers.expression import evaluate_and_append
from opteryx.models import QueryProperties

from . import BasePlanNode


class ProjectionNode(BasePlanNode):
    def __init__(self, properties: QueryProperties, **parameters):
        """
        Attribute Projection, remove unwanted columns and performs column renames.
        """
        BasePlanNode.__init__(self, properties=properties, **parameters)

        projection = parameters["projection"] + parameters.get("order_by_columns", [])

        self.projection = []
        for column in projection:
            self.projection.append(column.schema_column.identity)

        self.evaluations = [
            column for column in projection if column.node_type != NodeType.IDENTIFIER
        ]

        self.columns = parameters["projection"]

    @classmethod
    def from_json(cls, json_obj: str) -> "BasePlanNode":  # pragma: no cover
        raise NotImplementedError()

    @property
    def config(self):  # pragma: no cover
        from opteryx.managers.expression import format_expression

        return ", ".join(format_expression(col) for col in self.columns)

    @property
    def name(self):  # pragma: no cover
        return "Projection"

    def execute(self, morsel: pyarrow.Table) -> pyarrow.Table:
        if morsel == EOS:
            return EOS

        # If any of the columns need evaluating, we need to do that here
        morsel = evaluate_and_append(self.evaluations, morsel)
        return morsel.select(self.projection)