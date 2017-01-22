# git-squash.py

Squashes all commits of the current branch into one which contains a summary of all squashed commits with their subject and body, formatted for readability.

## Usage

Clone the repository and install the dependencies:

```bash
$ pip3 install click gitpython
```

You can pass numbers as arguments, which then get executed after which the script terminates, like: "python main.py 123".
Those numbers correspond to the different commands you see when running the script without any arguments.

If your branch does not branch off from `develop`, you can pass another origin with the `--branch my-branch` command line argument.

## Notes

* The current working directory is always used so it is preferable to have this script in your PATH
* Protected branches are `develop` and `master` by default but can be changed by changing the `protected_branches` variable

![](https://github.com/Gira-X/git-squash.py/raw/master/screencast/1.gif)
