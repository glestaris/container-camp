#!/bin/bash
set -e

dir_a=$1
dir_b=$2

rm -f diff.txt
diff -qNr $dir_a $dir_b > diff.txt || true # diff fails if it finds changes

files_a=($(cat diff.txt | cut -d ' ' -f 2))
files_b=($(cat diff.txt | cut -d ' ' -f 4))

echo "Found ${#files_a[@]} modified, new or deleted files!"

size=0
added_files=0
removed_files=0
modified_files=0
cnt=$((${#files_a[@]}-1))
for i in $(seq 0 $cnt); do
	file_a=${files_a[$i]}
	file_b=${files_b[$i]}

	if ! [ -e $file_b ]; then
		size=$(($size+15))
		removed_files=$(($removed_files+1))
	else
		file_size=$(du -b $file_b | cut -f 1)
		size=$(($size+$file_size))
		if ! [ -e $file_a ]; then
			added_files=$(($added_files+1))
		else
			modified_files=$(($modified_files+1))
		fi
	fi

	# ! [ -e $file_a ] && echo "$file_b is new in B!" && continue
	# ! [ -e $file_b ] && echo "$file_a was removed in B!"
	# echo "$file_a is changed in B!"
done

echo "The diff size is "$size"B"
echo "Added files: 	$added_files"
echo "Modified files: 	$modified_files"
echo "Removed files: 	$removed_files"
