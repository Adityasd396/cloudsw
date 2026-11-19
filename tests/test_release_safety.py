import tempfile,unittest
from pathlib import Path
from tools.build_release import validate_source

class ReleaseSourceSafetyTests(unittest.TestCase):
 def test_rejects_merge_markers_in_each_runtime_language(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder)
   for suffix in ['py','js','tsx','html','css','json','yml']:
    path=root/('source.'+suffix);path.write_text('before\n'+'<'*7+' HEAD\nold\n'+'='*7+'\nnew\n'+'>'*7+' branch\n',encoding='utf-8')
    with self.subTest(suffix=suffix),self.assertRaisesRegex(ValueError,'Unresolved merge conflict'):validate_source({path.name},root)
 def test_rejects_broken_python_and_json(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);(root/'app.py').write_text('def broken(',encoding='utf-8');(root/'release.json').write_text('{broken}',encoding='utf-8')
   with self.assertRaises(SyntaxError):validate_source({'app.py'},root)
   with self.assertRaises(ValueError):validate_source({'release.json'},root)
 def test_validates_without_changing_source(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);contents={'app.py':'value = 1\n','release.json':'{"version":"test"}','page.html':'<h1>Hello</h1>'}
   for name,content in contents.items():(root/name).write_text(content,encoding='utf-8')
   validate_source(contents,root)
   self.assertEqual({name:(root/name).read_text(encoding='utf-8') for name in contents},contents)
