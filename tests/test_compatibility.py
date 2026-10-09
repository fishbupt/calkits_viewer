def test_old_imports_match_package():
    import calkit_model
    import calkits_model
    import utils
    import xkt_parser
    from calkit_viewer import Standard, parse_xkt
    from calkit_viewer.export import write_snp

    assert calkit_model.Standard is Standard and calkits_model.Standard is Standard
    assert xkt_parser.parse_xkt is parse_xkt and utils.write_snp is write_snp
