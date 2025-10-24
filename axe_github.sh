#!/bin/bash

cat << "EOF"
     _________
    / ======= \
   / __________\
  | ___________ |
  | | -       | |
  | |         | |
  | |_________| |__________________________________
  \=____________/  PLEASE ENTER COMMIT MESSAGE:    )
  / """"""""""" \                       /
 / ::::::::::::: \                  =D-'
(_________________)


EOF

read -p "" commit_message

# Run tests
if [ "$1" = "test" ]; then
    if ! pytest; then
        echo "❌ Pytest failed. Aborting commit/push."
        exit 1
    fi
fi
# If pytest passed, continue:
git status
echo "=========================="
echo "=========================="

git add .
git commit -m "$commit_message"

# Try pushing
echo "🚀 Attempting to push..."
if ! git push; then
    echo "⚠️ Push failed. Attempting to set upstream..."
    current_branch=$(git rev-parse --abbrev-ref HEAD)
    echo "Current branch: $current_branch"
    echo
    echo

    if git push --set-upstream origin "$current_branch"; then
        echo "✅ Push succeeded after setting upstream."
    else
        echo "❌ Push failed even after setting upstream."
        exit 1
    fi
else
    echo "✅ Push succeeded."
fi

cat << "EOF"

            _____
           | |   \
           | |    \
           | |     \___
           | |         \
           | |          \
    0     _|_|___________|
   /\/  /____|____________) 
. /  \_|__________________| 
|/__    | )(            )(
| |\\  :| )(             )(


FANTASIA IMPROMPTU

==============================
EOF