import slugify as slugify_library

def slugify(value):
    return slugify_library.slugify(value, only_ascii=True)
