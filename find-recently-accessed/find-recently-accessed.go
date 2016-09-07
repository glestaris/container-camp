package main

import (
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"syscall"
	"time"
)

func usage() string {
	usage := ""
	usage += fmt.Sprintf("Filter files that have been accessed less than Y seconds ago in directory X.\n")
	usage += fmt.Sprintf("USAGE: %s <X> <Y>\n", os.Args[0])
	return usage
}

type cmdRequest struct {
	targetPath         string
	earliestAccessTime time.Time
}

func parseArgs(args []string) (cmdRequest, error) {
	// It should have excactly 2 string arguments
	if len(args) != 3 {
		return cmdRequest{}, errors.New("not enough arguments")
	}

	var req cmdRequest

	// Check target path
	req.targetPath = args[1]
	fi, err := os.Stat(req.targetPath)
	if err != nil {
		return cmdRequest{}, fmt.Errorf("`%s` does not exist: %s\n",
			req.targetPath, err,
		)
	}
	if !fi.IsDir() {
		return cmdRequest{}, errors.New(
			fmt.Sprintf("`%s` is not a directory\n", req.targetPath),
		)
	}

	// Calculate earliest access time
	seconds, err := strconv.ParseInt(args[2], 10, 32)
	if err != nil {
		return cmdRequest{}, fmt.Errorf("parsing '%s' as seconds: %s", args[2], err)
	}
	duration := time.Duration(-1*seconds) * time.Second
	req.earliestAccessTime = time.Now().Add(duration)

	return req, nil
}

type fileEntry struct {
	filePath string
	size     int64
}

func (req cmdRequest) do() ([]fileEntry, error) {
	entries := []fileEntry{}

	if err := filepath.Walk(req.targetPath,
		func(path string, fi os.FileInfo, err error) error {
			// skip non-regular files
			if !fi.Mode().IsRegular() {
				return nil
			}

			// is recently accessed?
			stat := fi.Sys().(*syscall.Stat_t)
			t := time.Unix(stat.Atim.Sec, stat.Atim.Nsec)
			if !t.After(req.earliestAccessTime) {
				return nil
			}

			// add to list
			entries = append(entries, fileEntry{
				filePath: path,
				size:     stat.Size,
			})

			return nil
		},
	); err != nil {
		return nil, err
	}

	return entries, nil
}

func main() {
	// parse request
	req, err := parseArgs(os.Args)
	if err != nil {
		fmt.Printf("ERROR: %s\n", err)
		fmt.Println("----------------------")
		fmt.Printf(usage())
		os.Exit(1)
	}

	// print request
	fmt.Printf("targetPath = '%s'\n", req.targetPath)
	fmt.Printf("earliestAccessTime = '%s'\n", req.earliestAccessTime.String())

	// run reqeust
	entries, err := req.do()
	if err != nil {
		fmt.Printf("ERROR: %s\n", err)
		os.Exit(1)
	}
	fmt.Printf("found %d entries!\n", len(entries))
	if len(entries) == 0 {
		os.Exit(0)
	}

	// calculate total size
	var totalSize int64
	for _, entry := range entries {
		totalSize += entry.size
	}
	fmt.Printf("Total size = %dB\n", totalSize)
	fmt.Printf("Total size = %dKB\n", totalSize/1024)
	fmt.Printf("Total size = %dMB\n", totalSize/1024/1024)
}
