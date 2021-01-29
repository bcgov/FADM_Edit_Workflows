def test_in_working_dir(working_dir, check='test'):
    """
    Simple check to be done in every TFL Tool. By default, checking if 'test' is in the working path
    anywhere

    Args:
        working_dir (str): a string respresenting the current working directory. Commonly built with
                    os.path.abspath(__file__)
        check (str): The string to search for in working dir to determine if 

    Returns:
        bool: True if the 'check' kwarg is in the working_dir string, False otherwise
    """
    test = False

    if check.lower() in working_dir.lower():
        test = True

    return test