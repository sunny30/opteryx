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
Optimization Rule - Limit Pushdown

Type: Heuristic
Goal: Reduce Rows

We try to push the limit to the other side of PROJECTS
"""

from opteryx.planner.logical_planner import LogicalPlan
from opteryx.planner.logical_planner import LogicalPlanNode
from opteryx.planner.logical_planner import LogicalPlanStepType

from .optimization_strategy import OptimizationStrategy
from .optimization_strategy import OptimizerContext


class LimitPushdownStrategy(OptimizationStrategy):
    def visit(self, node: LogicalPlanNode, context: OptimizerContext) -> OptimizerContext:
        if not context.optimized_plan:
            context.optimized_plan = context.pre_optimized_tree.copy()  # type: ignore

        if node.node_type == LogicalPlanStepType.Limit:
            node.nid = context.node_id
            context.collected_limits.append(node)
            return context

        if node.node_type in (
            LogicalPlanStepType.Join,
            LogicalPlanStepType.Scan,
            LogicalPlanStepType.AggregateAndGroup,
            LogicalPlanStepType.Aggregate,
            LogicalPlanStepType.Subquery,
            LogicalPlanStepType.Union,
            LogicalPlanStepType.Filter,
        ):
            # we don't push past here
            for limit_node in context.collected_limits:
                self.statistics.optimization_limit_pushdown += 1
                context.optimized_plan.remove_node(limit_node.nid, heal=True)
                context.optimized_plan.insert_node_after(
                    limit_node.nid, limit_node, context.node_id
                )
                limit_node.columns = []
            context.collected_limits.clear()

        return context

    def complete(self, plan: LogicalPlan, context: OptimizerContext) -> LogicalPlan:
        # No finalization needed for this strategy
        return plan