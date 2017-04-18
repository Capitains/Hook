from setuptools import setup, find_packages

setup(
    name='capitains-hook',
    version="1.0.0",
    description='Hook Flask App for Github/CTS repositories',
    url='http://github.com/Capitains/Hook',
    author='Thibault Clerice',
    author_email='leponteineptique@gmail.com',
    license='GNU GPL',
    packages=find_packages(exclude=("tests")),
    install_requires=[
        "Flask>=0.12",
        "flask-login>=0.4.0",
        "GitHub-Flask==2.1.1",
        "Flask-SQLAlchemy==2.2",
        "tabulate==0.7.7"
    ],
    tests_require=[
        "mock==2.0.0",
        "requests-mock==1.3.0",
        "beautifulsoup4==4.5.3"
    ],
    test_suite="tests",
    include_package_data=True,
    zip_safe=False
)
