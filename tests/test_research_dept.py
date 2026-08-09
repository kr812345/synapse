import unittest
from departments.research.manager import ResearchManager
from departments.research.reddit_worker import RedditWorker

class TestResearchDept(unittest.IsolatedAsyncioTestCase):
    async def test_research_manager_can_handle(self):
        manager = ResearchManager("rm_1", "Research Boss")
        self.assertTrue(manager.can_handle("do some research on AI"))
        self.assertFalse(manager.can_handle("write a python script"))

    async def test_research_workers(self):
        manager = ResearchManager("rm_1", "Research Boss")
        self.assertEqual(len(manager.workers), 3)
        self.assertIsInstance(manager.workers[0], RedditWorker)

if __name__ == "__main__":
    unittest.main()

