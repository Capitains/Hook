from setuptools import setup, find_packages


setup(
  name='Hook',
  version="0.0.1",
  description='Hook Flask App for Github/CTS repositories',
  url='http://github.com/Capitains/Hook',
  author='Thibault Clerice',
  author_email='leponteineptique@gmail.com',
  license='MIT',
  packages=find_packages(),
  install_requires=[
    "Flask==0.10.1",
    "flask-mongoengine==0.7.1",
    "flask-login==0.2.11",
    "GitHub-Flask==2.1.1",
    "GitPython==1.0.1",
    "MyCapytain==0.0.3",
    "unicode-slugify==0.1.3",
    "PyYAML==3.11"
  ],
  tests_require=[
    "Flask-Testing==0.4.2"
  ],
  test_suite="tests",
  zip_safe=False
)
