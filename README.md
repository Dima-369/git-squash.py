# git-squash

Squashes all commits of the current branch (if not develop or master) into one which contains a summary of all squased commits with their subject and body, formatted for readability.

## Usage

The script assumes the current working directory as the repo to work on.

You can pass numbers as arguments, which then get executed after which the script terminates, like: "python main.py 123".
Those numbers correspond to the different commands you see when running the script without any arguments.

Note that your branch should branch off from develop, as the script needs to detect the start of your branch.

The environment variable `$EDITOR` should be set which is used for entering git commit messages.

## TODO:

* Move to GitHub
* Option (YAML?) to only delete local/branch?

## Notes

* The current working directory is always used so it is preferable to have this script in your PATH
* Protected branches are `develop` and `master` for now but can be changed, TODO: where
