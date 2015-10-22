from setuptools import setup, find_packages

setup(
    name='Hook',
    version="0.0.1",
    description='Hook Flask App for Github/CTS repositories',
    url='http://github.com/Capitains/Hook',
    author='Thibault Clerice',
    author_email='leponteineptique@gmail.com',
    license='GNU GPL',
    packages=find_packages(exclude=("tests")),
    install_requires=[
        "Flask==0.10.1",
        "flask-mongoengine==0.7.1",
        "flask-login==0.2.11",
        "GitHub-Flask==2.1.1",
        "unicode-slugify==0.1.3",
        "PyYAML==3.11",
        "tornado==4.2.1"
    ],
    tests_require=[
        "Flask-Testing==0.4.2"
    ],
    test_suite="tests",
    include_package_data=True,
    zip_safe=False
)
