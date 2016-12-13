#!/usr/bin/env python3

import sys
import math
import operator
import functools
from pprint import pprint

import pyeda
import pyeda.inter 
# expr, expr2bdd, bddvar

def parse_puzzle(input_file):
    fin = open(input_file, 'r')
    lines = fin.readlines()

    puzzle = []
    for line in lines:
        puzzle.append( [ int(num) for num in line.split() ] )

    return puzzle

class BoolOp():

    # depth = 0

    def __init__(self, operator_ = '', operands = None):
        self.operator_ = operator_
        if operands == None:
            self.operands = []

    def set_operator(self, operator_):
        self.operator_ = operator_

    def append_operand(self, operand):
        self.operands.append(operand)

    def gen_pyeda_expr(self):
        # BoolOp.depth += 1
        pyeda_expr_ops = []

        for operand in self.operands:
            if type(operand) == str:
                expr_op = pyeda.inter.expr(operand)
            elif type(operand) == BoolOp:
                expr_op = operand.gen_pyeda_expr()

            pyeda_expr_ops.append(expr_op)

        if self.operator_ == 'AND':
            operator_ = pyeda.inter.And
        elif self.operator_ == 'OR':
            operator_ = pyeda.inter.Or
        elif self.operator_ == 'XOR':
            operator_ = pyeda.inter.Xor

        pyeda_expr = operator_(*pyeda_expr_ops)
        # BoolOp.depth -= 1
        return pyeda_expr

    def __bool__(self):
        return self.operands_count() != 0

    def operands_count(self):
        return len(self.operands)

    def operands_count_re(self):
        count = self.operands_count()

        for operand in self.operands:
            if type(operand) == BoolOp:
                count += operand.operands_count_re()

        return count

    def __str__(self):
        count = self.operands_count()
        return 'op: {}, count: {}, count resursive: {}\n'.format(self.operator_, count, self.operands_count_re())

    def __repr__(self):
        return str(self)


def block_to_row_col(block, index, size_square):
    '''return (row, col) of nth sudoku block's mth item.
    nth => block
    mth => index
    '''

    size = int(math.sqrt(size_square))
    row = (block // size) * size + (index // size)
    col = (block  % size) * size + (index  % size)

    return row, col

def bit_value(value, bit):
    '''return nth bit of value.
    nth => bit
    '''
    value = value >> bit
    return value % 2

def binary_encode_number_range(stop_num, binary_size, var_name):
    '''binary encoding an integer variable, whose range is between 0 and stop-1.
    '''

    assert stop_num <= 2**binary_size, 'number range should be in the binary size'
    if stop_num <= 0:
        return []

    # algorithm note
    # 
    # generate 0 ~ 24
    # stop_num = 25 = 11001 = 10000 + 1000 + 1
    #
    # [00 ~ 15] 10000 => 10000 => 0xxxx => ^x4
    # [16 ~ 23]  1000 => 11000 => 10xxx =>  x4 & ^x3
    # [     24]     1 => 11001 => 11000 =>  x4 &  x3 & ^x2 & ^x1 & ^x0
    #
    #                   base_val
    #
    # encoding = And(0xxxx, 10xxx, 11000) = ...

    base_val = 0
    result = BoolOp('OR')
    for bit in range(binary_size-1, -1, -1): # (binary = 4) => (3, 2, 1, 0)
        if bit_value(stop_num, bit) == 0:
            continue

        # bit value == 1
        base_val += 1 << bit 

        a = BoolOp('AND')
        for bit2 in range(binary_size-1, bit, -1):
            prefix = '' if bit_value(base_val, bit2) == 1 else '~'
            a.append_operand('{prefix}{name}{bit}'.format(prefix=prefix, name=var_name, bit=bit2))

        a.append_operand('~{name}{bit}'.format(name=var_name, bit=bit))
        result.append_operand(a)

    return result

def encode_puzzle(puzzle, size_square):

    binary_size = int(math.log2(size_square - 1)) + 1
    # 4 => 0 ~ 3 =>   00 ~   11 => binary size 2
    # 5 => 0 ~ 4 =>  000 ~  100 => binary size 3
    # 8 => 0 ~ 7 =>  000 ~  111 => binary size 3
    # 9 => 0 ~ 8 => 0000 ~ 1000 => binary size 4

    combination_2_list = combination_2(size_square)
    # variable: x_<row>_<col>_<bit>

    # 1.
    # for each row
        # for a, b in C(n, 2) in row
            # for each bit
                # a[bit] != b[bit]
            # '|'.join() # one bit difference is enough
        # '&'.join() # each two member must be different
    # '&'.join() # each row's requirement must be satisfy

    # 2. for each col
    # 3. for each block
    
    # 4. fill in variable value
    
    restrictions = BoolOp('AND') # each requirement must be satisfy

    # 1. for each row
    for row in range(size_square):

        row_restrict = BoolOp('AND') # each two member must be different
        for col1, col2 in combination_2_list:

            # print('row = ', row)
            # print(len(restrictions.operands))

            inequality = BoolOp('OR') # one bit difference is enough
            for bit in range(binary_size):
                # x[row][col1][bit] != x[row][col2][bit]
                # use xor operator for != (in boolean expression)
                bit_diff = 'x_{row}_{col1}_{bit} ^ x_{row}_{col2}_{bit}'.format(row=row, col1=col1, col2=col2, bit=bit)
                inequality.append_operand(bit_diff)

            row_restrict.append_operand(inequality)

        restrictions.append_operand(row_restrict)
    
    # 2. for each col
    for col in range(size_square):

        col_restrict = BoolOp('AND') # each two member must be different
        for row1, row2 in combination_2_list:

            inequality = BoolOp('OR') # one bit difference is enough
            for bit in range(binary_size):
                # x[row1][col][bit] != x[row2][col][bit]
                # use xor operator for != (in boolean expression)
                bit_diff = 'x_{row1}_{col}_{bit} ^ x_{row2}_{col}_{bit}'.format(row1=row1, row2=row2, col=col, bit=bit)
                inequality.append_operand(bit_diff)

            col_restrict.append_operand(inequality)

        restrictions.append_operand(col_restrict)

    # 3. for each block
    for block in range(size_square):

        block_restrict = BoolOp('AND') # each two member must be different
        for index1, index2 in combination_2_list:

            inequality = BoolOp('OR') # one bit difference is enough
            for bit in range(binary_size):
                # x[row1][col1][bit] != x[row2][col2][bit]
                # use xor operator for != (in boolean expression)
                row1, col1 = block_to_row_col(block, index1, size_square)
                row2, col2 = block_to_row_col(block, index2, size_square)

                bit_diff = 'x_{row1}_{col1}_{bit} ^ x_{row2}_{col2}_{bit}'.format(
                    row1=row1, row2=row2, col1=col1, col2=col2, bit=bit)
                inequality.append_operand(bit_diff)

            block_restrict.append_operand(inequality)

        restrictions.append_operand(block_restrict)

    print(size_square, binary_size)
    print(binary_encode_number_range(size_square, binary_size, 'x') == True)

    # 4. fill in number
    for row in range(size_square):
        for col in range(size_square):
            if puzzle[row][col] == 0:
                # from 0 ~ size_square - 1
                range_restrict = binary_encode_number_range(size_square, binary_size, 'x_{}_{}_'.format(row, col))

                # if stop_num == power(2, binary_size), then range_restrict == empty boolean expression
                # which means BoolOp with no operand, then __bool__() is false
                if range_restrict:
                    restrictions.append_operand(range_restrict)

                continue

            # for each cell != 0
            # set every bits to stable value
            cell_value = BoolOp('AND')
            for bit in range(binary_size):
                if bit_value(puzzle[row][col], bit) == 1:
                    cell_value.append_operand( 'x_{}_{}_{}'.format(row, col, bit) )
                else:
                    cell_value.append_operand( '~x_{}_{}_{}'.format(row, col, bit) )
                
            restrictions.append_operand(cell_value)
                    
    return restrictions

def combination_2(size):
    c = []
    for index1 in range(size):
        for index2 in range(index1+1, size):
            c.append((index1, index2))
    return c

# encoded_puzzle = 0
# puzzle_expr = 0
# puzzle_bdd = 0

def main():
    # global encoded_puzzle
    # global puzzle_expr
    # global puzzle_bdd

    if len(sys.argv) != 2:
        print('{} <input_file>'.format(sys.argv[0]))
       
    input_file = sys.argv[1]
    puzzle = parse_puzzle(input_file)
    puzzle_size_square = len(puzzle)

    encoded_puzzle = encode_puzzle(puzzle, puzzle_size_square)
    puzzle_expr = encoded_puzzle.gen_pyeda_expr()

    puzzle_bdd = pyeda.inter.expr2bdd(puzzle_expr)
    print(puzzle_bdd.satisfy_count())

if __name__ == '__main__':
    main()
