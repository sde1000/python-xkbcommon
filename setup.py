from setuptools import setup

def readme():
    with open('README.rst') as f:
        return f.read()

setup(name='xkbcommon',
      version='0.1',
      description='Bindings for libxkbcommon using cffi',
      long_description=readme(),
      classifiers=[
          'Development Status :: 3 - Alpha',
          'License :: OSI Approved :: MIT License',
          'Programming Language :: Python :: 3.5',
          'Topic :: Software Development :: Libraries',
          'Intended Audience :: Developers',
      ],
      url='https://github.com/sde1000/python-xkbcommon',
      author='Stephen Early',
      author_email='steve@assorted.org.uk',
      license='MIT',
      packages=['xkbcommon'],
      zip_safe=True,
      test_suite='tests.test_xkb',
      setup_requires=["cffi>=1.5.0"],
      install_requires=["cffi>=1.5.0"],
      cffi_modules=["ffi_build.py:ffibuilder"],
)
