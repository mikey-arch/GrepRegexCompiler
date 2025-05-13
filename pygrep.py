import sys
from collections import deque
from typing import List, Set, Optional, Union, Literal
from pydantic import BaseModel

class StateType(BaseModel):
    """Model representing a state type in the FSM"""
    value: Union[Literal["BR"], Literal["WC"], str]
    
    def model_post_init(self, __context):
        if self.value not in ["BR", "WC"] and len(self.value) != 1:
            raise ValueError("StateType must be 'BR', 'WC', or a single character")

class FSMState(BaseModel):
    """Model representing a state in the finite state machine"""
    state_num: int
    state_type: StateType
    next1: int
    next2: int

class FiniteStateMachine(BaseModel):
    """Model representing the entire finite state machine"""
    states: List[FSMState] = []
    
    def add_state(self, state_num: int, state_type: Union[str, StateType], next1: int, next2: int):
        """Add a new state to the FSM"""
        if isinstance(state_type, str):
            state_type = StateType(value=state_type)
        
        self.states.append(FSMState(
            state_num=state_num,
            state_type=state_type,
            next1=next1,
            next2=next2
        ))
    
    def get_state(self, state_num: int) -> Optional[FSMState]:
        """Get a state by number"""
        for state in self.states:
            if state.state_num == state_num:
                return state
        return None
    
    def update_state(self, state_num: int, next1: Optional[int] = None, next2: Optional[int] = None):
        """Update a state's next states"""
        for state in self.states:
            if state.state_num == state_num:
                if next1 is not None:
                    state.next1 = next1
                if next2 is not None:
                    state.next2 = next2
                return True
        return False
    
    def to_arrays(self):
        """Convert the FSM to arrays for the searcher"""
        sorted_states = sorted(self.states, key=lambda s: s.state_num)
        
        state_type_list = []
        next1_list = []
        next2_list = []
        
        for state in sorted_states:
            state_type_list.append(state.state_type.value)
            next1_list.append(state.next1)
            next2_list.append(state.next2)
            
        return state_type_list, next1_list, next2_list
    
    def print_fsm(self):
        """Print the FSM in the format: state_num,state_type,next1,next2"""
        sorted_states = sorted(self.states, key=lambda s: s.state_num)
        
        for state in sorted_states:
            print(f"{state.state_num},{state.state_type.value},{state.next1},{state.next2}")


class REcompiler:
    """Regular Expression Compiler that creates a finite state machine"""
    
    def __init__(self, regexp: str):
        """Initialize the compiler with the given regular expression pattern"""
        self.BR = "BR"       # Branch state indicator
        self.WC = "WC"       # Wildcard character
        self.END = -1        # End state marker
        
        # Parser state
        self.pattern = regexp + '\0'  # Append null terminator for parsing
        self.chars = list(self.pattern)   # Convert to character array
        self.pos = 0                    # Current position in pattern
        self.state_num = 1              # Current state number
        
        self.fsm = FiniteStateMachine()
        self.fsm.add_state(0, self.BR, 0, 0)
    
    def compile(self):
        """Compile the regex into a FSM and return it in array format"""
        initial_state = self.expression()
        
        # Check if we've consumed the entire pattern
        if self.chars[self.pos] != '\0':
            self.error("Not a proper regular expression - unexpected characters at end")
            
        # Connect dummy start to actual start (state 0 branches to initial state)
        self.fsm.update_state(0, initial_state, initial_state)
        
        # Add end marker state
        self.fsm.add_state(self.state_num, self.BR, self.END, self.END)
        
        # Convert to arrays for the searcher
        return self.fsm.to_arrays()
    
    def print_fsm(self):
        """Print the FSM in the required format"""
        self.fsm.print_fsm()
        
    def add_state(self, char_type: str, next_state1: int, next_state2: int):
        """Add a new state to the FSM"""
        self.fsm.add_state(self.state_num, char_type, next_state1, next_state2)
        self.state_num += 1
        return self.state_num - 1
        
    def set_state(self, state_id: int, char_type: str, next_state1: int, next_state2: int):
        """Set or update the given state"""
        state = self.fsm.get_state(state_id)
        if state:
            state.state_type = StateType(value=char_type)
            state.next1 = next_state1
            state.next2 = next_state2
        else:
            # Add new state
            self.fsm.add_state(state_id, char_type, next_state1, next_state2)
            # Also add any intermediate states if needed
            for i in range(len(self.fsm.states), state_id):
                self.fsm.add_state(i, self.BR, 0, 0)
        
    def expression(self):
        """Parse an expression (lowest precedence, handles alternation '|')"""
        # Save the state before this factor to handle alternation properly
        previous_state = self.state_num - 1
        
        # Parse the first term
        term1_state = self.term()
        result_state = term1_state
        
        if self.pos < len(self.chars) and self.chars[self.pos] == '|':
            state = self.fsm.get_state(previous_state)
            if state and state.next1 == state.next2:
                state.next2 = self.state_num
                
            if state:
                state.next1 = self.state_num
            
            previous_state = self.state_num - 1
            self.pos += 1
            
            # Create branch state for alternation
            result_state = self.state_num
            self.state_num += 1
            
            # Parse the second term (after '|')
            term2_state = self.expression()
            
            # Set the branch state to point to both terms
            self.set_state(result_state, self.BR, term1_state, term2_state)
            
            # Update previous states to point to the end
            state = self.fsm.get_state(previous_state)
            if state and state.next1 == state.next2:
                state.next2 = self.state_num
                
            if state:
                state.next1 = self.state_num
            
        return result_state
    
    def term(self):
        """Parse a term (concatenation of factors)"""
        result_state = self.factor()
        
        # Continue parsing factors as long as we see characters that could start a factor
        while (self.pos < len(self.chars) and 
               (self.is_vocab(self.chars[self.pos]) or 
                self.chars[self.pos] == '(' or 
                self.chars[self.pos] == '\\')):
            # Concatenation is implicit - just keep parsing factors
            self.factor()
            
        return result_state
    
    def factor(self):
        """Parse a factor (primary with optional quantifier: *, +, ?)"""
        # Parse the primary expression
        primary_state = self.primary()
        result_state = primary_state
        
        if self.pos < len(self.chars):
            # Handle zero or one '?' operator
            if self.chars[self.pos] == '?':
                # Get primary state and update
                primary = self.fsm.get_state(primary_state)
                if primary:
                    primary.next1 = self.state_num + 1
                    primary.next2 = self.state_num + 1
                
                # Create branch state that either enters primary or skips it
                self.set_state(self.state_num, self.BR, primary_state, self.state_num + 1)
                
                self.pos += 1
                result_state = self.state_num
                self.state_num += 1
                
            # Handle one or more '+' operator
            elif self.chars[self.pos] == '+':
                # Create branch state for repetition
                self.set_state(self.state_num, self.BR, primary_state, self.state_num + 1)
                
                self.pos += 1
                # Return primary as entry point (ensures at least one match)
                result_state = primary_state
                self.state_num += 1
                
            # Handle zero or more '*' operator 
            elif self.chars[self.pos] == '*':
                # Create branch state for repetition or skip
                self.set_state(self.state_num, self.BR, self.state_num + 1, primary_state)
                
                self.pos += 1
                result_state = self.state_num
                self.state_num += 1
        
        return result_state
    
    def primary(self):
        """Parse a primary element (literal, escaped char, wildcard, subexpression)"""
        result_state = -10  # Default error value
        
        if self.pos < len(self.chars):
            # Handle escaped character
            if self.chars[self.pos] == '\\':
                self.pos += 1  # Move past the backslash
                
                # Check if there's a character after the backslash
                if self.pos < len(self.chars):
                    # Create a state for the escaped character
                    self.set_state(self.state_num, self.chars[self.pos], self.state_num + 1, self.state_num + 1)
                    self.pos += 1
                    result_state = self.state_num
                    self.state_num += 1
                else:
                    self.error("Escape at end of pattern")
            
            # Handle normal character or wildcard
            elif self.is_vocab(self.chars[self.pos]):
                if self.chars[self.pos] == '.':
                    # Handle wildcard - matches any character
                    self.set_state(self.state_num, self.WC, self.state_num + 1, self.state_num + 1)
                else:
                    # Handle literal character
                    self.set_state(self.state_num, self.chars[self.pos], self.state_num + 1, self.state_num + 1)
                
                self.pos += 1
                result_state = self.state_num
                self.state_num += 1
            
            # Handle parenthesized subexpression
            elif self.chars[self.pos] == '(':
                self.pos += 1  # Move past the opening parenthesis
                
                # Parse the subexpression
                result_state = self.expression()
                
                # Check for closing parenthesis
                if self.pos < len(self.chars) and self.chars[self.pos] == ')':
                    self.pos += 1
                else:
                    self.error("Missing closing parenthesis")
            else:
                self.error(f"Unexpected character: {self.chars[self.pos]}")
        else:
            self.error("Unexpected end of pattern")
            
        return result_state
    
    def is_vocab(self, char):
        """Check if a character is a normal vocabulary character (not special)"""
        return char not in "()\\*+?|" and char != '\0'
    
    def error(self, message):
        """Report a compilation error and exit"""
        current_char = self.chars[self.pos] if self.pos < len(self.chars) else "EOL"
        sys.stderr.write(f"Error: {message} - near '{current_char}'\n")
        sys.exit(1)
        

class REsearcher:
    """Regular Expression Searcher that uses a compiled FSM"""
    
    def __init__(self, state_type, next1, next2):
        """Initialize the searcher with the given FSM components"""
        self.state_type = state_type
        self.next1 = next1
        self.next2 = next2
        
        self.BR = "BR"     # Branch state indicator
        self.WC = "WC"     # Wildcard state indicator
        self.END = -1      # End state marker
        self.SCAN = -1     # Scan marker for deque
        
        self._validate_fsm()
        
    def _validate_fsm(self):
        """Validate the FSM structure using Pydantic models"""
        try:
            # Create FSM model from arrays
            fsm = FiniteStateMachine()
            for i in range(len(self.state_type)):
                fsm.add_state(
                    i, 
                    self.state_type[i],
                    self.next1[i],
                    self.next2[i]
                )
        except Exception as e:
            sys.stderr.write(f"Invalid FSM structure: {str(e)}\n")
            sys.exit(1)
        
    def search_file(self, filename):
        """Search for pattern matches in the given file"""
        matching_lines = []
        
        try:
            with open(filename, 'r', encoding='utf-8') as file:
                for line in file:
                    # Strip newline and check for match
                    line = line.rstrip('\n')
                    if self.search_pattern_in_line(line):
                        matching_lines.append(line)
        except Exception as e:
            sys.stderr.write(f"Error reading file {filename}: {str(e)}\n")
            sys.exit(1)
            
        return matching_lines
    
    def search_pattern_in_line(self, line):
        """Search for a pattern match at any position in the line"""
        # Try matching from each position in the line
        for pos in range(len(line)):
            if self.match_from_position(line, pos):
                return True
        return False
    
    def match_from_position(self, line, start_pos):
        """Attempt to match the pattern from the specified position"""
        # Initialize the deque with scan marker and add start state
        deq = deque()
        deq.append(self.SCAN)
        self.add_state(deq, 0)
        
        pos = start_pos
        consumed_input = False
        
        # Process states until we find a match or exhaust possibilities
        while deq:
            state = deq.popleft()
            
            # Handle the SCAN marker that separates current and next states
            if state == self.SCAN:
                if not deq:
                    return False  
                
                # Move to next character and add new scan marker
                if pos < len(line):
                    pos += 1
                    consumed_input = True
                    deq.append(self.SCAN)
                continue
            
            # Check if we've reached an end state
            if self.is_end_br_state(state) and consumed_input:
                return True  
            
            # Handle branch state - add both next states to the front
            if state < len(self.state_type) and self.state_type[state] == self.BR:
                self.add_state(deq, self.next1[state])
                self.add_state(deq, self.next2[state])
                continue
            
            # Skip if we've reached the end of the line
            if pos >= len(line):
                continue
            
            # Handle wildcard and literal character match
            input_char = line[pos]
            if state < len(self.state_type):
                if self.state_type[state] == self.WC:
                    deq.append(self.next1[state])
                elif len(self.state_type[state]) == 1 and self.state_type[state] == input_char:
                    deq.append(self.next1[state])
        
        return False
    
    def add_state(self, deq, state):
        """Add a state to the deque, handling branch states recursively"""
        if state < 0:
            return  # Invalid or end state
        
        visited = set()
        self.add_state_recursive(deq, state, visited)
    
    def add_state_recursive(self, deq, state, visited):
        """Recursively add a state to the deque to handle branch states"""
        if state < 0 or state in visited:
            return
        
        visited.add(state)
        
        # End BR state, add to deque to mark match completion
        if self.is_end_br_state(state):
            deq.appendleft(state)
            return
        
        # If branch state, traverse its next states
        if state < len(self.state_type) and self.state_type[state] == self.BR:
            self.add_state_recursive(deq, self.next1[state], visited)
            self.add_state_recursive(deq, self.next2[state], visited)
        else:
            deq.appendleft(state)
    
    def is_end_br_state(self, state):
        """Check if the state is an end branch state"""
        if state < 0 or state >= len(self.state_type):
            return False
        
        return (self.state_type[state] == self.BR and 
                self.next1[state] == self.END and 
                self.next2[state] == self.END)


def main():
    """Main entry point for the program"""
    if len(sys.argv) < 2:
        sys.stderr.write("Usage: python pygrep.py <regexp> [file]\n")
        sys.exit(1)
        
    regexp = sys.argv[1]
    
    try:
        compiler = REcompiler(regexp)
        
        # Compile the regular expression into an FSM
        state_type, next1, next2 = compiler.compile()
        
        # If no file provided, just print the FSM and exit
        if len(sys.argv) < 3:
            compiler.print_fsm()
            return
        
        # Otherwise, search the specified file
        filename = sys.argv[2]
        searcher = REsearcher(state_type, next1, next2)
        matching_lines = searcher.search_file(filename)
        
        for line in matching_lines:
            print(line)
            
    except Exception as e:
        sys.stderr.write(f"Error: {str(e)}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
