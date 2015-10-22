import slugify as slugify_library


def slugify(value):
    """ Slugify a string

    :param value: String to HookUI.slugify
    :return: Slug
    """
    return slugify_library.slugify(value, only_ascii=True)