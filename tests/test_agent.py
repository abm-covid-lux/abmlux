"""Test the Agent object, which is pretty simple"""

import unittest
from abmlux.agent import Agent, AgentType

class TestAgent(unittest.TestCase):
    """Test the agent object, which stores agent config"""

    def test_agent_age_categories(self):
        """Test that agents report as the correct type based on age"""

        expected = {0: AgentType.CHILD,
                    10: AgentType.CHILD,
                    18: AgentType.ADULT,
                    45: AgentType.ADULT,
                    65: AgentType.RETIRED,
                    99: AgentType.RETIRED}

        for age, typ in expected.items():
            new_agent = Agent(age)
            assert new_agent.agetyp == typ
            assert new_agent.age == age

    def test_agent_age_beyond_bounds(self):
        """Ensure ages cannot be out of the configured type bounds"""

        self.assertRaises(ValueError, Agent, -1)
        self.assertRaises(ValueError, Agent, 130)

    # TODO: Add location adding and activity lookup
