# git-squash.py

Python3 script to squash all commits of the current branch into one which contains a summary of all squashed commits with their subject and body, formatted for readability.

## Usage

Clone the repository and install the dependencies:

```shell
$ pip3 install click gitpython
```

You can pass numbers as arguments, which then get executed after which the script terminates, like: "python main.py 123".
Those numbers correspond to the different commands you see when running the script without any arguments.

If your branch does not branch off from `develop`, you can pass another origin with the `--branch my-branch` command line argument.

## Notes

* The current working directory is always used so it is preferable to have this script in your PATH
* Protected branches are `develop` and `master` by default but can be changed by changing the `protected_branches` variable

![](https://github.com/Gira-X/git-squash.py/raw/master/screencast/1.gif)

## Options on running the script

```json
0:  alias for 123458 (default behavior)
1:  Pull 'master' and switch back to current branch 'test'
2:  Rebase branch 'master' onto current branch 'test'
3:  Squash current branch 'test' into a single commit
4:  Merge current branch 'test' into 'master' with --no-ff
5:  Delete local and remote branch 'test' and switch to 'master'
------------
6:  Count commits to squash
7:  Check if merge will lead to conflicts
8:  Exit
```
