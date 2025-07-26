from awslabs.rds_management_mcp_server.common.context import RDSContext


def test_context_creation():
    assert isinstance(RDSContext, type)


def test_context_readonly_mode():
    assert isinstance(RDSContext.readonly_mode(), bool)


def test_context_max_items():
    assert isinstance(RDSContext.max_items(), int)


def test_context_get_pagination_config():
    config = RDSContext.get_pagination_config()
    assert isinstance(config, dict)
    assert 'MaxItems' in config


def test_context_initialize():
    RDSContext.initialize(readonly=False, max_items=200)
    assert RDSContext.readonly_mode() is False
    assert RDSContext.max_items() == 200

    # Reset to default values
    RDSContext.initialize()
    assert RDSContext.readonly_mode() is True
    assert RDSContext.max_items() == 100
