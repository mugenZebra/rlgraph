# Copyright 2018 The YARL-Project, All Rights Reserved.
#
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
# ==============================================================================

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from yarl import get_backend
from yarl.utils import root_logger, force_list
from yarl.graphs import GraphBuilder
from yarl.graphs.graph_executor import GraphExecutor
from yarl.tests.test_util import recursive_assert_almost_equal


class ComponentTest(object):
    """
    A simple (and limited) Graph-wrapper to test a single component in an easy, straightforward way.
    """
    def __init__(self, component, input_spaces=None, action_space=None, seed=10, logging_level=None):
        """
        Args:
            component (Component): The Component to be tested (may contain sub-components).
            input_spaces (Optional[dict]): Dict with component's API methods' names as keys and lists of Space objects
                or Space specs as values. Describes the input Spaces for the component.
                None, if the Component to be tested has no API methods with input parameters.
            action_space (Optional[Space]): The action space to pass into the GraphBuilder.
            seed (Optional[int]): The seed to use for random-seeding the Model object.
                If None, do not seed the Graph (things may behave non-deterministically).
            logging_level (Optional[int]): When provided, sets YARL's root_logger's logging level to this value.
        """
        self.seed = seed
        if logging_level is not None:
            root_logger.setLevel(logging_level)

        # Create a GraphBuilder.
        self.graph_builder = GraphBuilder(action_space=action_space)

        # Add the component to test and expose all its Sockets to the core component of our Model.
        self.graph_builder.set_core_component(component)

        # Build the model.
        self.graph_executor = GraphExecutor.from_spec(
            get_backend(),
            graph_builder=self.graph_builder,
            execution_spec=dict(seed=self.seed)
        )
        self.graph_executor.build(input_spaces)

    def test(self, api_method, params=None, expected_outputs=None, decimals=7, fn_test=None):
        """
        Does one test pass through the component to test.

        Args:
            api_method (str): The name of the API-method of the GraphBuilders core-Copmonent to call.
            params (Union[list,tuple]): The parameters to pass into the API-method.
            expected_outputs (Optional[any]): The expected return value(s) generated by the API-method.
                If None, no checks will be done on the output.
            decimals (Optional[int]): The number of digits after the floating point up to which to compare actual
                outputs and expected values.
            fn_test (Optional[callable]): Test function to call with (self, outs) as parameters.

        Returns:
            any: The actual returned values when calling the API-method with the given parameters.
        """
        # Get the outs ..
        outs = self.graph_executor.execute(api_method, *force_list(params))

        #  Optionally do test asserts here.
        if expected_outputs is not None:
            self.assert_equal(outs, expected_outputs, decimals=decimals)

        if callable(fn_test):
            fn_test(self, outs)

        return outs

    def variable_test(self, variables, expected_values):
        """
        Asserts that all given `variables` have the `expected_values`.
        Variables can be given in an arbitrary structure including nested ones.

        Args:
            variables (any): Any structure that contains variables.
            expected_values (any): Matching structure with the expected values for the given variables.
        """
        values = self.get_variable_values(variables)
        self.assert_equal(values, expected_values)

    def get_variable_values(self, *variables):
        """
        Executes a session to retrieve the values of the provided variables.

        Args:
            variables (Union[variable,List[variable]]): Variable objects whose values to retrieve from the graph.

        Returns:
            any: Values of the variables provided.
        """
        ret = self.graph_executor.read_variable_values(variables)
        if len(variables) == 1:
            return ret[0]
        return ret

    @staticmethod
    def assert_equal(outs, expected_outputs, decimals=7):
        """
        Convenience wrapper: See implementation of `recursive_assert_almost_equal` for details.
        """
        recursive_assert_almost_equal(outs, expected_outputs, decimals=decimals)
