from xsharp_helper import InvalidSyntax, Position
from xsharp_lexer import TT, Token

## NODES

class Statements:
	def __init__(self, start_pos: Position, end_pos: Position, body: list):
		self.start_pos = start_pos
		self.end_pos = end_pos
		self.body = body

	def __repr__(self):
		res: str = "[\n"
		for line in self.body:
			res += "  " + repr(line) + "\n"
		return res + "]"

class IntLiteral:
	def __init__(self, value: int, start_pos: Position, end_pos: Position):
		self.value = value
		self.start_pos = start_pos
		self.end_pos = end_pos
		self.in_parentheses = False
	
	def __repr__(self):
		return f"Literal[{self.value}]"
	
class Identifier:
	def __init__(self, symbol: str, start_pos: Position, end_pos: Position):
		self.symbol = symbol
		self.start_pos = start_pos
		self.end_pos = end_pos
		self.in_parentheses = False
	
	def __repr__(self):
		return f"Identifier[{self.symbol}]"

class BinaryOperation:
	def __init__(self, left, op: Token, right):
		self.left = left
		self.op = op
		self.right = right
		self.in_parentheses = False
	
	def __repr__(self):
		return f"({self.left}, {self.op}, {self.right})"

class UnaryOperation:
	def __init__(self, op: Token, value):
		self.op = op
		self.value = value
		self.in_parentheses = False
	
	def __repr__(self):
		return f"({self.op}, {self.value})"

class ConstDefinition:
	def __init__(self, symbol: Identifier, value: IntLiteral):
		self.symbol = symbol
		self.value = value
	
	def __repr__(self):
		return f"ConstDef[{self.symbol} -> {self.value}]"

class VarDeclaration:
	def __init__(self, identifier: str, value):
		self.identifier = identifier
		self.value = value

	def __repr__(self):
		return f"VarDeclaration[{self.identifier}] -> {self.value}"

class ForLoop:
	def __init__(self, start_pos: Position, end_pos: Position, identifier: str, start: int, end: int, step: int, body: Statements):
		self.start_pos = start_pos
		self.end_pos = end_pos
		self.identifier = identifier
		self.start = start
		self.end = end
		self.step = step
		self.body = body

## PARSE RESULT
class ParseResult:
	def __init__(self):
		self.node, self.error = None, None
	
	def register(self, res):
		if isinstance(res, ParseResult):
			self.error = res.error
		return res.node
	
	def success(self, node):
		self.node = node
		return self
	
	def fail(self, error):
		self.error = error
		return self
	
	def __str__(self):
		return repr(self.node)

## PARSER
class Parser:
	def __init__(self, tokens: list[Token]):
		self.tokens = tokens
		self.current_token = None
		self.token_index = -1
		self.advance()
	
	def advance(self):
		self.token_index += 1
		if self.token_index < len(self.tokens):
			self.current_token = self.tokens[self.token_index]
	
	def parse(self):
		res = ParseResult()

		ast = res.register(self.statements())
		if res.error: return res

		if self.current_token.token_type != TT.EOF:
			return res.fail(InvalidSyntax(
				self.current_token.start_pos, self.current_token.end_pos,
				"Expected an operator."
			))

		return res.success(ast)
	
	def statements(self, end=(TT.EOF, )):
		res = ParseResult()
		body = []
		more_statements = True

		while more_statements:
			while self.current_token.token_type == TT.NEWLINE: self.advance()
			start_pos = self.current_token.start_pos

			if self.current_token.token_type in end:
				end_pos = self.current_token.end_pos
				more_statements = False
				break

			stmt = res.register(self.statement())
			if res.error: return res

			body.append(stmt)

			if self.current_token.token_type in end:
				end_pos = self.current_token.end_pos
				more_statements = False
		
		return res.success(Statements(start_pos, end_pos, body))

	def statement(self):
		if self.current_token.token_type == TT.KEYWORD:
			match self.current_token.value:
				case "define": return self.const_definition()
				case "var": return self.var_declaration()
				case "for": return self.for_loop()

		return self.expression()

	def const_definition(self):
		res = ParseResult()
		self.advance()

		identifier = res.register(self.literal())
		if res.error: return res

		if not isinstance(identifier, Identifier):
			return res.fail(InvalidSyntax(
				identifier.start_pos, identifier.end_pos,
				"Expected an identifier after 'define' keyword."
			))
		
		value = res.register(self.literal())
		if res.error: return res

		if not isinstance(value, IntLiteral):
			return res.fail(InvalidSyntax(
				value.start_pos, value.end_pos,
				"Expected an identifier after 'define' keyword."
			))
		
		return res.success(ConstDefinition(identifier, value))

	def var_declaration(self):
		res = ParseResult()
		self.advance()

		if self.current_token.token_type != TT.IDENTIFIER:
			return res.fail(InvalidSyntax(
				self.current_token.start_pos, self.current_token.end_pos,
				"Expected an identifier after 'var' keyword."
			))
		identifier = self.current_token.value
		self.advance()

		expr = res.register(self.expression())
		if res.error: return res

		if self.current_token.token_type not in (TT.NEWLINE, TT.EOF):
			return res.fail(InvalidSyntax(
				self.current_token.start_pos, self.current_token.end_pos,
				"Expected a newline or EOF after variable declaration."
			))
		
		return res.success(VarDeclaration(identifier, expr))

	def for_loop(self):
		res = ParseResult()
		start_pos = self.current_token.start_pos
		self.advance()

		if self.current_token.token_type != TT.IDENTIFIER:
			return res.fail(InvalidSyntax(
				self.current_token.start_pos, self.current_token.end_pos,
				"Expected an identifier after 'for' keyword."
			))
		identifier = self.current_token.value
		self.advance()

		if self.current_token != Token(None, None, TT.KEYWORD, "start"):
			return res.fail(InvalidSyntax(
				self.current_token.start_pos, self.current_token.end_pos,
				"Expected 'start' keyword after iterator."
			))
		self.advance()
		if self.current_token.token_type != TT.COL:
			return res.fail(InvalidSyntax(
				self.current_token.start_pos, self.current_token.end_pos,
				"Expected ':' after 'start' keyword."
			))
		self.advance()
		if self.current_token.token_type != TT.NUM:
			return res.fail(InvalidSyntax(
				self.current_token.start_pos, self.current_token.end_pos,
				"Expected a start value."
			))
		start = self.current_token.value
		self.advance()

		if self.current_token != Token(None, None, TT.KEYWORD, "end"):
			return res.fail(InvalidSyntax(
				self.current_token.start_pos, self.current_token.end_pos,
				"Expected 'end' keyword after start value."
			))
		self.advance()
		if self.current_token.token_type != TT.COL:
			return res.fail(InvalidSyntax(
				self.current_token.start_pos, self.current_token.end_pos,
				"Expected ':' after 'end' keyword."
			))
		self.advance()
		if self.current_token.token_type != TT.NUM:
			return res.fail(InvalidSyntax(
				self.current_token.start_pos, self.current_token.end_pos,
				"Expected an end value."
			))
		end = self.current_token.value
		self.advance()

		if self.current_token != Token(None, None, TT.KEYWORD, "step"):
			return res.fail(InvalidSyntax(
				self.current_token.start_pos, self.current_token.end_pos,
				"Expected 'step' keyword after iterator."
			))
		self.advance()
		if self.current_token.token_type != TT.COL:
			return res.fail(InvalidSyntax(
				self.current_token.start_pos, self.current_token.end_pos,
				"Expected ':' after 'step' keyword."
			))
		self.advance()
		if self.current_token.token_type != TT.NUM:
			return res.fail(InvalidSyntax(
				self.current_token.start_pos, self.current_token.end_pos,
				"Expected a step value."
			))
		step = self.current_token.value
		self.advance()

		if self.current_token.token_type != TT.LBR:
			return res.fail(InvalidSyntax(
				self.current_token.start_pos, self.current_token.end_pos,
				"Expected '{' before for loop body."
			))
		self.advance()

		body = res.register(self.statements(end=(TT.EOF, TT.RBR)))
		if res.error: return res

		if self.current_token.token_type != TT.RBR:
			return res.fail(InvalidSyntax(
				self.current_token.start_pos, self.current_token.end_pos,
				"Expected '}' after for loop body."
			))
		end_pos = self.current_token.end_pos
		self.advance()

		return res.success(ForLoop(start_pos, end_pos, identifier, start, end, step, body))

	def expression(self):
		return self.logical()

	def binary_op(self, func, token_types: tuple[TT]):
		res = ParseResult()

		left = res.register(func())
		if res.error: return res

		while self.current_token.token_type in token_types:
			op = self.current_token
			self.advance()

			right = res.register(func())
			if res.error: return res

			left = BinaryOperation(left, op, right)
		
		return res.success(left)
	
	def logical(self):
		return self.binary_op(self.additive, (TT.AND, TT.OR, TT.XOR))
	
	def additive(self):
		return self.binary_op(self.unary, (TT.ADD, TT.SUB))
	
	def unary(self):
		res = ParseResult()

		if self.current_token.token_type in (TT.ADD, TT.SUB, TT.NOT):
			tok = self.current_token
			self.advance()
			value = res.register(self.unary())
			if res.error: return res
			return res.success(UnaryOperation(tok, value))
		
		value = res.register(self.literal())
		if res.error: return res

		if self.current_token.token_type in (TT.INC, TT.DEC):
			tok = self.current_token
			self.advance()
			return res.success(UnaryOperation(tok, value))
		
		return res.success(value)
	
	def literal(self):
		res = ParseResult()
		tok = self.current_token
		self.advance()

		if tok.token_type == TT.NUM:
			return res.success(IntLiteral(tok.value, tok.start_pos, tok.end_pos))
		
		if tok.token_type == TT.IDENTIFIER:
			return res.success(Identifier(tok.value, tok.start_pos, tok.end_pos))
		
		if tok.token_type == TT.LPR:
			expr = res.register(self.expression())
			if res.error: return res

			if self.current_token.token_type != TT.RPR:
				return res.fail(InvalidSyntax(self.current_token.start_pos, self.current_token.end_pos, "Expected a matching right parenthesis."))
			self.advance()

			expr.in_parentheses = True
			return res.success(expr)

		return res.fail(InvalidSyntax(tok.start_pos, tok.end_pos, f"Expected a number, an identifier or '(', found token '{tok.token_type}' instead."))
