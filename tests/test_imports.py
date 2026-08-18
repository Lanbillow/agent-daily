"""接口冻结冒烟：所有模块可导入、关键符号存在。"""

import unittest


class TestImports(unittest.TestCase):
    def test_all_modules_importable(self):
        from agent_daily import config, doctor  # noqa: F401
        from agent_daily import model, prompt, agent, tools, output, jobs, storage  # noqa: F401

    def test_key_symbols_exist(self):
        from agent_daily.model import ModelManager, ModelProvider
        from agent_daily.prompt import PromptManager
        from agent_daily.agent import NullMemory, WorkflowAgent
        from agent_daily.tools import ToolRegistry
        from agent_daily.output import OutputRegistry
        from agent_daily.storage import ArtifactStore, StateStore
        from agent_daily.jobs import JobRegistry

        # Protocol 不能实例化
        with self.assertRaises(TypeError):
            ModelProvider()
        # 容器类可直接实例化
        self.assertEqual(ToolRegistry().names(), [])
        self.assertEqual(OutputRegistry().names(), [])
        # NullMemory 是无状态空实现
        self.assertEqual(NullMemory().load_context(), {})
        NullMemory().save_context({"x": 1})  # 不抛异常


if __name__ == "__main__":
    unittest.main()
