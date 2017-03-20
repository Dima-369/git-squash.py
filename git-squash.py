import os
import re
import subprocess
import sys
import tempfile
from collections import namedtuple
from subprocess import call
from subprocess import check_output

import click
from git import Repo, NoSuchPathError, InvalidGitRepositoryError

CommitMessage = namedtuple('CommitMessage', 'subject body')

# script will refuse to squash those branches
protected_branches = ['master', 'develop']

# both are initialized in main() and not modified afterwards
active_branch = None
merge_on = None


def extract_branch_from_name_rev(s):
    return re.findall(r"(?<= )[^~^]*", s)[0]


def extract_commit_head_summary(s):
    s = s.strip().split('\n')
    if len(s) == 1:
        return CommitMessage(subject=s[0], body='')
    else:
        return CommitMessage(subject=s[0], body='\n'.join(s[2:]))


def construct_commit_body(commits):
    result = ''
    for i, c in enumerate(commits):
        result += '## {subject}\n\n'.format(subject=c.subject)
        if len(c.body) > 0:
            result += '{body}\n\n'.format(body=c.body)
    return result.strip().replace('"', '\\"')


def get_first_branch_commit_sha():
    def throw_git_log_error():
        print("Can not checkout branch '{b}'. Did you set --branch in the "
              "command line arguments?".format(b=merge_on))
        sys.exit(1)

    output = ""
    try:
        output = subprocess.check_output(
            "git log {onto}..{branch} --oneline --no-color | tail -1".format(
                onto=merge_on, branch=active_branch), shell=True) \
            .decode("utf-8")
        if output == "":
            throw_git_log_error()
    except subprocess.CalledProcessError:
        throw_git_log_error()
    return re.findall(r"[^ ]*", output)[0]


def pull_merge_on_branch_and_checkout_active():
    print('')
    os.system('git checkout {merge_on}'.format(merge_on=merge_on))
    os.system('git pull')
    os.system('git checkout {branch}'.format(branch=active_branch))


def get_commits_to_squash(r):
    commits = []
    first = get_first_branch_commit_sha()
    for c in r.iter_commits(rev=active_branch):
        commits.append(extract_commit_head_summary(c.message))
        if c.hexsha.startswith(first):
            break
    return commits


def call_os(*args):
    o = check_output(*args).decode('utf-8')
    return o


def call_os_print_output(*args):
    o = check_output(*args).decode('utf-8')
    print(o)
    return o


def probe_rebase_conflicts():
    def cleanup():
        call_os(['git', 'merge', '--abort'])
        call_os(['git', 'checkout', active_branch])

    print()
    call_os(['git', 'checkout', merge_on])
    try:
        check_output(['git', 'merge', '--no-commit', '--no-ff', active_branch])
        cleanup()
        input("No conflicts detected! Proceed with return: ")
        return
    except subprocess.CalledProcessError:
        print("Squash/merge will lead to conflicts!")
    input("\nYou can inspect your working directory and accept with Return. "
          "The test merge will be reverted then!")
    cleanup()


def squash_branch(r):
    commits = get_commits_to_squash(r)
    if len(commits) == 1:
        print('Can not squash because there is only 1 commit!')
        return False
    print('Going to squash {commits} commits into one'
          .format(commits=len(commits)))
    body = construct_commit_body(commits)
    subject = get_subject_input(body)
    if subject == '':
        print('Aborting...')
        return True
    os.system('git reset --soft HEAD~{count}'.format(count=len(commits)))
    os.system('git commit -m "{subject}\n\n{body}"'
              .format(subject=subject, body=body))
    return False


def rebase_branch():
    print()
    call_os(['git', 'checkout', active_branch])
    try:
        call_os(['git', 'rebase', merge_on])
    except subprocess.CalledProcessError:
        print('Rebase has lead to conflicts. Fix them manually!')
        sys.exit(1)


def get_script_path():
    return os.path.dirname(os.path.realpath(__file__))


def get_editor():
    return os.environ['EDITOR']


def get_merge_template_message(body):
    r = '\n\n# Enter the git subject message above\n# This will be the body:\n#'
    for line in body.split('\n'):
        r += '\n# {line}'.format(line=line)
    return r


def get_subject_input(body):
    with tempfile.NamedTemporaryFile() as f:
        f.write(bytes(get_merge_template_message(body), 'UTF-8'))
        f.flush()
        call([get_editor(), f.name])
        f.seek(0)
        r = f.read().decode('UTF-8')
    final = ''
    for line in r.split('\n'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        final += line
    final = final.strip()
    if final.count('\n') > 1:
        print('Your subject is multi line!')
        return ''
    if len(final) > 50:
        print('Your subject is longer than 50 characters!')
        return ''
    return final


def merge_into_branch():
    call_os(['git', 'checkout', merge_on])
    try:
        call(['git', 'merge', '--no-ff', '--edit', active_branch])
    except subprocess.CalledProcessError:
        print('You got merge conflicts because your branch was not correctly '
              'rebased!')
        print('Reverting merge...')
        call_os(['git', 'reset', '--merge'])
        return True
    return False


def purge_branches():
    """Returns true if the user aborted the operation"""

    def delete_remote_branch():
        try:
            call_os(['git', 'push', 'origin', ':{branch}'
                    .format(branch=active_branch)])
        except subprocess.CalledProcessError:
            print('Failed to delete the origin branch. This can be ignored!')

    def delete_local_branch():
        call_os(['git', 'branch', '-D', active_branch])

    print("\nChoose how to delete the branch '{b}'".format(b=active_branch))
    print("0:  Delete local and remote branch")
    print("1:  Delete local branch only")
    print("2:  Delete remote branch only")
    print("3:  Skip deletion")
    choice = input("\nChoice (0-3): ").strip()

    if choice == '0':
        call_os(['git', 'checkout', merge_on])
        delete_local_branch()
        delete_remote_branch()
    elif choice == '1':
        call_os(['git', 'checkout', merge_on])
        delete_local_branch()
    elif choice == '2':
        call_os(['git', 'checkout', merge_on])
        delete_remote_branch()


def print_commits_to_squash(r):
    commits = get_commits_to_squash(r)
    print("There are {count} commits to be squashed:"
          .format(count=len(commits)))
    for commit in commits:
        print('* {subject}'.format(subject=commit.subject))


def process_input(r, s, dividers=True):
    def print_dividers():
        if dividers:
            print('-------------------------------------------------------')

    print_dividers()
    for c in s:
        if c == '0':
            pull_merge_on_branch_and_checkout_active()
            rebase_branch()
            if squash_branch(r):
                break
            if merge_into_branch():
                break
            purge_branches()
            sys.exit(0)
        if c == '1':
            pull_merge_on_branch_and_checkout_active()
        elif c == '2':
            rebase_branch()
        elif c == '3':
            if squash_branch(r):
                break
        elif c == '4':
            if merge_into_branch():
                break
        elif c == '5':
            purge_branches()
        elif c == '6':
            print_commits_to_squash(r)
        elif c == '7':
            probe_rebase_conflicts()
        elif c == '8':
            sys.exit(0)
        else:
            print('Unrecognized command: {char}'.format(char=c))
            print_dividers()
            break
        print_dividers()


def input_loop(r):
    def print_options():
        current = 'current branch \'{b}\''.format(b=b)
        print('Currently on branch \'{branch}\' and will '
              'merge into branch \'{onto}\'\n'.format(branch=b, onto=merge_on))
        print("0:  alias for 123458 (default behavior)")
        print("1:  Pull '{onto}' and switch back to {c}"
              .format(onto=merge_on, c=current))
        print("2:  Rebase branch '{onto}' onto {c}"
              .format(onto=merge_on, c=current))
        print("3:  Squash {c} into a single commit".format(c=current))
        print("4:  Merge {c} into '{onto}' with --no-ff"
              .format(c=current, onto=merge_on))
        print("5:  Delete local and remote branch '{b}' and switch to '{onto}'"
              .format(b=b, onto=merge_on))
        print("------------")
        print("6:  Count commits to squash")
        print("7:  Check if merge will lead to conflicts")
        print("8:  Exit")
        print("")

    # caching the initial branch for operations
    b = r.active_branch.name
    while True:
        print_options()
        try:
            i = input("Choice (0-8): ")
        except KeyboardInterrupt:
            sys.exit(0)
        process_input(r, i)


@click.command()
@click.option('--branch', default='develop',
              help='The origin branch on which to merge (default: develop)')
@click.argument('execute', type=click.INT, required=False)
def main(execute, branch):
    """Squashes git commits on the current branch.

    If EXECUTE is passed, that action is launched and the script exits,
    otherwise the script prompts for actions on stdin."""
    global merge_on

    def check_editor_environ():
        try:
            os.environ["EDITOR"]
        except KeyError:
            print("Set the environment variable $EDITOR to edit "
                  "commit messages! Aborting...")
            sys.exit(1)

    def get_repo():
        try:
            return Repo('.')
        except (NoSuchPathError, InvalidGitRepositoryError):
            print('Directory is not a git repo!')
            sys.exit(3)

    def validate_repo():
        global active_branch

        def can_squash():
            return len(get_commits_to_squash(r)) >= 2

        if r.is_dirty() or len(r.untracked_files) > 0:
            print('Repository is dirty or has untracked files! Aborting...')
            sys.exit(2)
        active_branch = r.active_branch.name
        if active_branch in protected_branches:
            print("Current branch \"{branch}\" is protected! "
                  "Aborting...".format(branch=active_branch))
            sys.exit(1)
        if active_branch == branch:
            print("Trying to merge and squash onto same branch \"{branch}\"!\n"
                  "Is your --branch argument correct? --branch specifies the "
                  "branch on which your current branch should be merged on.\n"
                  "Aborting...".format(branch=active_branch))
            sys.exit(1)
        if not can_squash():
            print('There is only one commit to be squashed on '
                  'branch \'{branch}\'. Squashing is disabled!'
                  .format(branch=active_branch))
        call_os_print_output(['git', 'checkout', branch])
        status = call_os_print_output(['git', 'status'])
        call_os_print_output(['git', 'checkout', active_branch])
        if 'Your branch is ahead of ' in status:
            print('The branch you want to merge in: {branch} is '
                  'ahead of origin. Push first!'.format(branch=branch))
            sys.exit(1)

    merge_on = branch
    check_editor_environ()
    r = get_repo()
    validate_repo()
    if execute:
        process_input(r, execute, dividers=False)
    else:
        input_loop(r)


if __name__ == '__main__':
    main()
