# AI Runtime IR Specification v0.1

This document defines the Instruction Representation (IR) for the AI Runtime. This IR serves as the "Pixel ISA for Thought," a structured, auditable language for expressing complex plans and workflows.

Each instruction is represented as a JSON object with an `op` field and an `args` dictionary.

---

## Core Operations (15 Ops)

### 1. State and Flow Control

#### `ASSERT`
- **Description**: Evaluates a predicate. If the predicate is false, the execution halts with an error. Used for preconditions, postconditions, and invariants.
- **Args**:
    - `predicate`: `string` - An expression to be evaluated (e.g., `"result > 0"`).
    - `message`: `string` - An error message to display if the assertion fails.
- **Example**: `{"op": "ASSERT", "args": {"predicate": "len(data) > 0", "message": "Input data cannot be empty."}}`

#### `TRACE`
- **Description**: Logs a message or the value of a variable to the execution trace for observability and debugging.
- **Args**:
    - `message`: `string` - The message to log. Can include variable placeholders.
    - `data`: `any` (optional) - A variable or literal to include in the trace.
- **Example**: `{"op": "TRACE", "args": {"message": "Data loaded successfully.", "data": {"record_count": 1024}}}`

#### `RETURN`
- **Description**: Terminates the program and returns a final value.
- **Args**:
    - `value`: `any` - The value to return from the program.
- **Example**: `{"op": "RETURN", "args": {"value": {"status": "complete", "result": 42}}}`

### 2. Skill and Tool Execution

#### `CALL`
- **Description**: Executes a deterministic skill from the Skill Library (Σ).
- **Args**:
    - `skill`: `string` - The name of the skill to execute (e.g., `"http_get"`).
    - `params`: `dict` - A dictionary of arguments to pass to the skill.
    - `result_to`: `string` - The name of the variable to store the result in.
- **Example**: `{"op": "CALL", "args": {"skill": "http_get", "params": {"url": "https://api.example.com/data"}, "result_to": "api_response"}}`

#### `SIMULATE`
- **Description**: Runs a sandboxed simulation using a world-model from the Skill Library (Σ). This is for "what-if" scenarios.
- **Args**:
    - `environment`: `string` - The name of the simulation environment.
    - `params`: `dict` - The initial parameters for the simulation.
    - `result_to`: `string` - The variable to store the simulation outcome.
- **Example**: `{"op": "SIMULATE", "args": {"environment": "market_model", "params": {"price_change": -0.1}, "result_to": "market_impact"}}`

### 3. Data Operations

#### `READ`
- **Description**: Reads data from a source, such as the filesystem or a database table from Memory (Μ).
- **Args**:
    - `source`: `string` - The source to read from (e.g., `"file"`, `"db"`).
    - `identifier`: `string` - The path to the file or the name of the table.
    - `result_to`: `string` - The variable to store the loaded data.
- **Example**: `{"op": "READ", "args": {"source": "file", "identifier": "/data/input.csv", "result_to": "csv_data"}}`

#### `WRITE`
- **Description**: Writes data to a destination.
- **Args**:
    - `destination`: `string` - The destination to write to (e.g., `"file"`, `"db"`).
    - `identifier`: `string` - The path to the file or the name of the table.
    - `data`: `any` - The variable or literal to write.
- **Example**: `{"op": "WRITE", "args": {"destination": "file", "identifier": "/data/output.json", "data": {"result": 42}}}`

#### `PARSE`
- **Description**: Transforms raw data (e.g., string) into a structured format (e.g., JSON, CSV).
- **Args**:
    - `format`: `string` - The target format (e.g., `"json"`, `"csv"`, `"xml"`).
    - `data`: `string` - The raw data to parse.
    - `result_to`: `string` - The variable to store the parsed data.
- **Example**: `{"op": "PARSE", "args": {"format": "json", "data": "{\\"key\\": \\"value\\"}", "result_to": "parsed_json"}}`

#### `FORMAT`
- **Description**: Renders structured data into a string format.
- **Args**:
    - `format`: `string` - The output format (e.g., `"json_string"`, `"markdown_table"`).
    - `data`: `any` - The structured data to format.
    - `result_to`: `string` - The variable to store the formatted string.
- **Example**: `{"op": "FORMAT", "args": {"format": "markdown_table", "data": [{"a":1}, {"a":2}], "result_to": "md_table"}}`

### 4. Collection and Graph Operations

#### `MAP`
- **Description**: Applies a skill or a simple expression to each element in a collection.
- **Args**:
    - `collection`: `list` - The input collection.
    - `transform`: `string` - The skill or expression to apply.
    - `result_to`: `string` - The variable to store the new collection.
- **Example**: `{"op": "MAP", "args": {"collection": [1, 2, 3], "transform": "x -> x * 2", "result_to": "doubled_list"}}`

#### `FILTER`
- **Description**: Selects elements from a collection that satisfy a predicate.
- **Args**:
    - `collection`: `list` - The input collection.
    - `predicate`: `string` - The predicate to apply to each element.
    - `result_to`: `string` - The variable to store the filtered collection.
- **Example**: `{"op": "FILTER", "args": {"collection": [1, 2, 3, 4], "predicate": "x -> x % 2 == 0", "result_to": "even_numbers"}}`

#### `REDUCE`
- **Description**: Combines elements of a collection into a single value using a reducer function.
- **Args**:
    - `collection`: `list` - The input collection.
    - `reducer`: `string` - The reducer function (e.g., `"sum"`, `"average"`).
    - `initial_value`: `any` (optional) - The starting value.
    - `result_to`: `string` - The variable to store the final value.
- **Example**: `{"op": "REDUCE", "args": {"collection": [1, 2, 3, 4], "reducer": "sum", "result_to": "total"}}`

#### `JOIN`
- **Description**: Joins two data collections based on a key.
- **Args**:
    - `left_collection`: `list` - The first collection.
    - `right_collection`: `list` - The second collection.
    - `join_on`: `string` - The key to join on.
    - `result_to`: `string` - The variable to store the joined collection.
- **Example**: `{"op": "JOIN", "args": {"left_collection": "users", "right_collection": "orders", "join_on": "user_id", "result_to": "user_orders"}}`

### 5. Planning and Search

#### `SEARCH`
- **Description**: Performs a search over a state space (e.g., a graph in Memory (Μ) or a set of web pages) using a heuristic.
- **Args**:
    - `space`: `string` - The search space (e.g., `"web"`, `"knowledge_graph"`).
    - `query`: `string` - The search query.
    - `heuristic`: `string` (optional) - The heuristic to guide the search.
    - `budget`: `int` (optional) - The resource budget (e.g., number of steps).
    - `result_to`: `string` - The variable to store the search results.
- **Example**: `{"op": "SEARCH", "args": {"space": "web", "query": "latest AI research", "budget": 10, "result_to": "search_results"}}`

#### `REFINE`
- **Description**: Takes a high-level plan or abstract goal and refines it into a more detailed sequence of IR instructions.
- **Args**:
    - `plan`: `any` - The abstract plan or goal to refine.
    - `context`: `any` (optional) - Additional context to guide the refinement.
    - `result_to`: `string` - The variable to store the refined plan (a list of IR nodes).
- **Example**: `{"op": "REFINE", "args": {"plan": "Analyze sales data", "context": {"timeframe": "Q4"}, "result_to": "detailed_sales_plan"}}`
