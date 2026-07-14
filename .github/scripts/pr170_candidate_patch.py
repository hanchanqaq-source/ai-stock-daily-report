from pathlib import Path


path = Path("tests/test_system_config_service.py")
text = path.read_text(encoding="utf-8")
replacements = [
    (
        '''        self.assertEqual(items["LLM_DEEPSEEK_API_KEY"]["value"], "sk-test-value")
        self.assertEqual(items["LLM_DEEPSEEK_MODELS"]["value"], "deepseek-v4-flash,deepseek-v4-pro")
        self.assertEqual(items["LLM_MY_PROXY_API_KEYS"]["value"], "sk-key-1,sk-key-2")
''',
        '''        self.assertEqual(items["LLM_DEEPSEEK_API_KEY"]["value"], payload["mask_token"])
        self.assertTrue(items["LLM_DEEPSEEK_API_KEY"]["is_masked"])
        self.assertTrue(items["LLM_DEEPSEEK_API_KEY"]["raw_value_exists"])
        self.assertEqual(items["LLM_DEEPSEEK_MODELS"]["value"], "deepseek-v4-flash,deepseek-v4-pro")
        self.assertEqual(items["LLM_MY_PROXY_API_KEYS"]["value"], payload["mask_token"])
        self.assertTrue(items["LLM_MY_PROXY_API_KEYS"]["is_masked"])
        self.assertTrue(items["LLM_MY_PROXY_API_KEYS"]["raw_value_exists"])
        self.assertNotIn("sk-test-value", str(payload))
        self.assertNotIn("sk-key-1", str(payload))
''',
    ),
    (
        '''            self.assertEqual(pre_save_items["OPENAI_API_KEY"]["value"], "runtime-openai-key")
            self.assertFalse(pre_save_items["OPENAI_API_KEY"]["raw_value_exists"])
''',
        '''            self.assertEqual(pre_save_items["OPENAI_API_KEY"]["value"], "")
            self.assertFalse(pre_save_items["OPENAI_API_KEY"]["is_masked"])
            self.assertFalse(pre_save_items["OPENAI_API_KEY"]["raw_value_exists"])
            self.assertNotIn("runtime-openai-key", str(pre_save))
''',
    ),
    (
        '''                {"key": "LITELLM_MODEL", "value": ""},
                {"key": "OPENAI_MODEL", "value": ""},
                {"key": "OPENAI_BASE_URL", "value": ""},
                {"key": "OPENAI_API_KEY", "value": ""},
''',
        '''                {"key": "LITELLM_MODEL", "value": ""},
                {"key": "OPENAI_MODEL", "value": ""},
                {"key": "OPENAI_BASE_URL", "value": ""},
                {"key": "OPENAI_API_KEY", "action": "clear"},
''',
    ),
    (
        '''                {"key": "LLM_HERMES_API_KEYS", "value": ""},
                {"key": "LLM_HERMES_EXTRA_HEADERS", "value": ""},
''',
        '''                {"key": "LLM_HERMES_API_KEYS", "action": "clear"},
                {"key": "LLM_HERMES_EXTRA_HEADERS", "action": "clear"},
''',
    ),
    (
        '''        validation = self.service.validate(
            items=[
                {"key": "FEISHU_FOLDER_TOKEN", "value": ""},
            ]
        )
''',
        '''        validation = self.service.validate(
            items=[
                {"key": "FEISHU_FOLDER_TOKEN", "action": "clear"},
            ]
        )
''',
    ),
]

for old, new in replacements:
    old_count = text.count(old)
    new_count = text.count(new)
    if old_count == 1 and new_count == 0:
        text = text.replace(old, new)
        continue
    if old_count == 0 and new_count == 1:
        continue
    raise SystemExit(
        f"candidate replacement state invalid: old={old_count}, new={new_count}, snippet={old[:80]!r}"
    )

path.write_text(text, encoding="utf-8")
