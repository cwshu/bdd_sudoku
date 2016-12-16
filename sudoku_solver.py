#!/usr/bin/env python3

import sys
import math
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
    '''Expression tree, boolean operation node
    '''

    pyeda_op = {
        'AND': pyeda.inter.And,
        'OR': pyeda.inter.Or,
        'XOR': pyeda.inter.Xor,
    }

    def __init__(self, operator_ = '', operands = None):
        self.operator_ = operator_
        if operands == None:
            self.operands = []

    def set_operator(self, operator_):
        self.operator_ = operator_

    def append_operand(self, operand):
        self.operands.append(operand)

    def gen_pyeda_expr(self):
        pyeda_expr_ops = []

        for operand in self.operands:
            if type(operand) in (str, int):
                expr_op = pyeda.inter.expr(operand)
            elif type(operand) == BoolOp:
                expr_op = operand.gen_pyeda_expr()

            pyeda_expr_ops.append(expr_op)

        pyeda_expr = BoolOp.pyeda_op[self.operator_](*pyeda_expr_ops)
        return pyeda_expr

    def __bool__(self):
        return self.operands_count() != 0

    def operands_count(self):
        return len(self.operands)

    def operands_count_recursive(self):
        count = self.operands_count()

        for operand in self.operands:
            if type(operand) == BoolOp:
                count += operand.operands_count_recursive()

        return count

    def __str__(self):
        count = self.operands_count()
        return 'op: {}, count: {}, count resursive: {}\n'.format(self.operator_, count, self.operands_count_recursive())

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

def combination_2(size):
    c = []
    for index1 in range(size):
        for index2 in range(index1+1, size):
            c.append((index1, index2))
    return c


def binary_encode_number_range(stop_num, binary_size, var_name):
    '''binary encoding an integer variable, whose range is between 0 and stop-1.
    '''

    assert stop_num <= 2**binary_size, 'number range should be in the binary size'
    if stop_num <= 0:
        return BoolOp()
        '''
        # if stop_num == power(2, binary_size), then range_restrict == empty boolean expression
        # which means BoolOp with no operand, then __bool__() is false
        if range_restrict:
            puzzle_restrict.append_operand(range_restrict)
        '''

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

class SudokuEncodeBox():

    def __init__(self, puzzle):
        self.puzzle = puzzle

        self.size_square = len(puzzle)
        self.binary_size = int(math.log2(self.size_square - 1)) + 1

    def encoded_cell_bit(self, row, col, bit):
        '''if cell doesn't have value: return encoded literal
           else: return value(0 or 1)
        '''
        if self.puzzle[row][col] == 0:
            return 'x_{row}_{col}_{bit}'.format(row=row, col=col, bit=bit)
        else:
            return bit_value(self.puzzle[row][col], bit)

    def inequality_for_each_2_elements(self, elements, binary_size):

        # AND(e1 != e2, e1 != e3, ... ) # C(n, 2) for n elements
        # e1 != e2: OR(e1.b1 ^ e2.b1, e1.b2 ^ e2.b2, e1.b3 ^ e2.b3 ... ) # to b[m] for binary_size m
        if len(elements) <= 1:
            return None

        combination_2_list = combination_2(len(elements))

        each_ineqality = BoolOp('AND') # each 2 elements wouldn't be same.
        for e1_idx, e2_idx in combination_2_list: # e1: element1

            e1 = elements[e1_idx]
            e2 = elements[e2_idx]

            inequality = BoolOp('OR') # one bit difference is enough
            for bit in range(binary_size):
                # use xor operator for != (in boolean expression)
                bit_diff = BoolOp('XOR')
                bit_diff.append_operand(self.encoded_cell_bit(row=e1[0], col=e1[1], bit=bit))
                bit_diff.append_operand(self.encoded_cell_bit(row=e2[0], col=e2[1], bit=bit))

                inequality.append_operand(bit_diff)

            each_ineqality.append_operand(inequality)

        return each_ineqality

    def encode_single_cell(self, row, col):
        if self.puzzle[row][col] == 0:
            # from 0 ~ size_square - 1
            return binary_encode_number_range(self.size_square, self.binary_size, 'x_{}_{}_'.format(row, col))
        else:
            # for each cell != 0
            # set every bits to stable value
            cell_value = BoolOp('AND')
            for bit in range(self.binary_size):
                if bit_value(self.puzzle[row][col], bit) == 1:
                    cell_value.append_operand( 'x_{}_{}_{}'.format(row, col, bit) )
                else:
                    cell_value.append_operand( '~x_{}_{}_{}'.format(row, col, bit) )
            return cell_value
        
    def encode_each_cell(self):
        puzzle_restrict = BoolOp('AND')

        for row in range(self.size_square):
            for col in range(self.size_square):
                encoded_cell = self.encode_single_cell(row, col)
                if encoded_cell:
                    puzzle_restrict.append_operand(encoded_cell)

        return puzzle_restrict

    def encode(self):
        # 4 => 0 ~ 3 =>   00 ~   11 => binary size 2
        # 5 => 0 ~ 4 =>  000 ~  100 => binary size 3
        # 8 => 0 ~ 7 =>  000 ~  111 => binary size 3
        # 9 => 0 ~ 8 => 0000 ~ 1000 => binary size 4

        # variable: x_<row>_<col>_<bit>

        # 1. for each row
            # inequality_each(all elements in row)
        # 2. for each col
        # 3. for each block
        # 4. fill in variable value

        restrictions = BoolOp('AND') # each requirement must be satisfy
        # 1. for each row
            # x[row][col1][bit] != x[row][col2][bit]
        for row in range(self.size_square):
            row_elements = [ (row, col_index) for col_index in range(self.size_square) ]
            row_restrict = self.inequality_for_each_2_elements(row_elements, self.binary_size)
            restrictions.append_operand(row_restrict)
        
        # 2. for each col
            # x[row1][col][bit] != x[row2][col][bit]
        for col in range(self.size_square):
            col_elements = [ (row_index, col) for row_index in range(self.size_square) ]
            col_restrict = self.inequality_for_each_2_elements(col_elements, self.binary_size)
            restrictions.append_operand(col_restrict)

        # 3. for each block
            # x[row1][col1][bit] != x[row2][col2][bit]
        for block in range(self.size_square):
            block_elements = [ block_to_row_col(block, index, self.size_square) for index in range(self.size_square) ]
            block_restrict = self.inequality_for_each_2_elements(block_elements, self.binary_size)
            restrictions.append_operand(block_restrict)
            # print('block_elements: ', block_elements)

        # print(self.size_square, self.binary_size)
        # print(binary_encode_number_range(self.size_square, self.binary_size, 'x') == True)

        # 4. fill in number
        cells_restriction = self.encode_each_cell()
        restrictions.operands.extend(cells_restriction.operands) # little dirty.
                        
        return restrictions

# encoded_puzzle = 0
# puzzle_expr = 0
# puzzle_bdd = 0

def main():
    # global encoded_puzzle
    # global puzzle_expr
    # global puzzle_bdd

    if len(sys.argv) != 2:
        print('argument error: {} <input_file>'.format(sys.argv[0]))
        sys.exit(1)
       
    input_file = sys.argv[1]
    puzzle = parse_puzzle(input_file)

    sudoku_box = SudokuEncodeBox(puzzle)
    encoded_puzzle = sudoku_box.encode()
    # print('encoded')
    puzzle_expr = encoded_puzzle.gen_pyeda_expr()
    # print('generate pyeda.expr()')

    puzzle_bdd = pyeda.inter.expr2bdd(puzzle_expr)
    print(puzzle_bdd.satisfy_count())

# ret = binary_encode_number_range(16, 4, 'x_1_2_')
if __name__ == '__main__':
    main()
