# Grep - Regular Expression Pattern Searcher

A Python implementation that combines regular expression compilation and searching into a unified grep-like utility.

## Overview

Compiles a regular expression into a finite state machine (FSM) and uses that FSM to search for matching patterns in text files. It's based on the principles of non-deterministic finite automata for pattern matching.

## Features

- **Regular Expression Support:**
  - Literal characters match themselves
  - `.` wildcard matches any single character
  - `*` zero or more repetitions of the preceding expression
  - `+` one or more repetitions of the preceding expression
  - `?` zero or one occurrence of the preceding expression
  - `|` alternation (matches either expression)
  - `(` and `)` for grouping expressions
  - `\` escapes special characters

- **FSM Compiler:**
  - Parses regular expressions using recursive descent parsing
  - Builds a non-deterministic finite automaton (NFA)
  - Uses branch states for alternation and repetition operations

- **Pattern Matcher:**
  - Implements an efficient NFA simulation using a deque
  - Supports matching at any position in a line of text
  - Outputs lines that contain matching patterns

## Usage

```bash
# Display the FSM for a regular expression
python pygrep.py "regex_pattern"

# Search for matches in a file
python pygrep.py "regex_pattern" filename.txt

# Example
python pygrep.py "cat|dog" animalbook.txt
```

## How It Works

- Compilation Phase:

    - Parses the regular expression into a syntax tree
    - Converts the syntax tree into a non-deterministic finite automaton
    - Represents the NFA as a set of states with transitions


- Search Phase:

    - For each line in the input file, attempts to match the pattern
    - Maintains a set of possible current states during matching
    - Uses a scan marker to separate current states from next states
    - Reports lines containing matches
