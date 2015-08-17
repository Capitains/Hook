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
    "requests==2.7.0",
    "six==1.9.0",
    "lxml==3.4.4",
    "future==0.14.3"
  ],
  test_suite="tests",
  zip_safe=False
)
