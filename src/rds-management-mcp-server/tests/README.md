# RDS Management MCP Server Tests

This directory contains comprehensive tests for the RDS Management MCP Server, covering all tools, resources, and functionality.

## Test Structure

The tests are organized by module:

- `test_server.py`: Tests for the main server module, MCP initialization, and tool definitions
- `test_cluster.py`: Tests for cluster management operations (create, modify, delete, etc.)
- `test_resources.py`: Tests for resource implementations (RDS cluster resources)
- `test_utils.py`: Tests for utility functions

## Running the Tests

### Prerequisites

- Python 3.8 or higher
- Pytest installed (`pip install pytest pytest-asyncio`)
- AWS credentials configured (for integration tests)

### Running All Tests

```bash
# From the project root directory
pytest -v tests/

# With coverage report
pytest --cov=awslabs.rds_management_mcp_server tests/
```

### Running Specific Test Files

```bash
# Run only the server tests
pytest -v tests/test_server.py

# Run only the cluster tests
pytest -v tests/test_cluster.py
```

### Running Specific Tests

```bash
# Run a specific test class
pytest -v tests/test_server.py::TestServerConfiguration

# Run a specific test method
pytest -v tests/test_server.py::TestServerConfiguration::test_version_constant
```

## Test Configuration

- Tests use `pytest` fixtures defined in `conftest.py`
- Mock AWS resources are used to avoid actual AWS calls during testing
- Integration tests can be enabled by setting specific environment variables

## Test Coverage

These tests provide coverage for:

1. **Server Functionality**
   - Server initialization and configuration
   - MCP object configuration
   - Command line argument handling
   
2. **Tools**
   - All MCP tools defined in the server
   - All parameter variations and error conditions
   - Read-only mode vs. write mode behavior

3. **Resources**
   - Cluster listing resource
   - Cluster details resource
   - Error handling for resources

4. **Utility Functions**
   - Validation functions
   - Formatting functions
   - Error handling utilities
   - AWS interaction helpers

## Adding New Tests

When adding new functionality to the server:

1. Create corresponding test cases in the appropriate test file
2. Ensure both success and failure paths are tested
3. Use mocks to avoid actual AWS calls
4. Verify readonly mode behavior for all operations
5. Add any new fixtures to `conftest.py`

## Integration Testing

While unit tests use mocks, integration testing with actual AWS resources can be enabled with:

```bash
# Set to 'true' to allow actual AWS calls
export RDS_MCP_INTEGRATION_TESTS=true

# Run integration tests (marked with the integration marker)
pytest -v -m integration
```

**Note**: Integration tests may incur AWS charges and should be used carefully.
