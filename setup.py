from setuptools import setup, find_packages

version = '0.1'

setup(name='tvdbpy',
      version=version,
      description="The TvDB API client.",
      keywords='tvdb api client',
      author='Matias Bordese',
      author_email='mbordese@gmail.com',
      url='http://github.com/matiasb/tvdbpy',
      license='BSD',
      packages=find_packages(),
)
