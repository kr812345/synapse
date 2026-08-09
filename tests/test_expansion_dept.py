import unittest
from departments.engineering.manager import EngineeringManager
from departments.engineering.backend_worker import BackendWorker
from departments.marketing.manager import MarketingManager
from departments.marketing.social_worker import SocialWorker
from departments.personal.manager import PersonalManager
from departments.personal.assistant_worker import AssistantWorker

class TestExpansionDepartments(unittest.IsolatedAsyncioTestCase):
    async def test_engineering_department(self):
        manager = EngineeringManager("eng_1", "Eng Boss")
        self.assertTrue(manager.can_handle("engineering task"))
        self.assertEqual(len(manager.workers), 1)
        self.assertIsInstance(manager.workers[0], BackendWorker)

    async def test_marketing_department(self):
        manager = MarketingManager("mkt_1", "Marketing Boss")
        self.assertTrue(manager.can_handle("marketing task"))
        self.assertEqual(len(manager.workers), 1)
        self.assertIsInstance(manager.workers[0], SocialWorker)

    async def test_personal_department(self):
        manager = PersonalManager("per_1", "Personal Boss")
        self.assertTrue(manager.can_handle("personal task"))
        self.assertEqual(len(manager.workers), 1)
        self.assertIsInstance(manager.workers[0], AssistantWorker)

if __name__ == "__main__":
    unittest.main()
