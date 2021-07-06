import os
import subprocess
import unittest.mock

import pytest

from pre_commit_hooks.forbid_new_submodules import main


@pytest.fixture
def git_dir_with_git_dir(tmpdir):
    with tmpdir.as_cwd():
        subprocess.check_call(('git', 'init', '.'))
        subprocess.check_call((
            'git', 'commit', '-m', 'init', '--allow-empty', '--no-gpg-sign',
        ))
        subprocess.check_call(('git', 'init', 'foo'))
        subprocess.check_call(
            ('git', 'commit', '-m', 'init', '--allow-empty', '--no-gpg-sign'),
            cwd=str(tmpdir.join('foo')),
        )
        yield


@pytest.mark.parametrize(
    'cmd',
    (
        # Actually add the submodule
        ('git', 'submodule', 'add', './foo'),
        # Sneaky submodule add (that doesn't show up in .gitmodules)
        ('git', 'add', 'foo'),
    ),
)
def test_main_new_submodule(git_dir_with_git_dir, capsys, cmd):
    subprocess.check_call(cmd)
    assert main(()) == 0
    assert main(('random_non-related_file',)) == 0
    assert main(('foo',)) == 1
    out, _ = capsys.readouterr()
    assert out.startswith('foo: new submodule introduced\n')


def test_main_new_submodule_committed(git_dir_with_git_dir, capsys):
    REV_PARSE_HEAD = ('git', 'rev-parse', 'HEAD')
    FROM = subprocess.check_output(REV_PARSE_HEAD).decode().strip()
    subprocess.check_call(('git', 'submodule', 'add', './foo'))
    subprocess.check_call(('git', 'commit', '-m', 'new submodule'))
    TO = subprocess.check_output(REV_PARSE_HEAD).decode().strip()
    with unittest.mock.patch.dict(
        os.environ,
        {'PRE_COMMIT_FROM_REF': FROM, 'PRE_COMMIT_TO_REF': TO},
        clear=True,
    ):
        assert main(()) == 0
        assert main(('random_non-related_file',)) == 0
        assert main(('foo',)) == 1
    out, _ = capsys.readouterr()
    assert out.startswith('foo: new submodule introduced\n')


def test_main_no_new_submodule(git_dir_with_git_dir):
    open('test.py', 'a+').close()
    subprocess.check_call(('git', 'add', 'test.py'))
    assert main(()) == 0
    assert main(('test.py',)) == 0
