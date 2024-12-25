INSTANCE_METADATA = {
    'example1.txt': {'sat': True, 'unique': False},
    'example2.txt': {'sat': False, 'unique': False},
    'example3.txt': {'sat': False, 'unique': True},
    'example4.txt': {'sat': False, 'unique': False},
    'example5.txt': {'sat': True, 'unique': True},
    'example6.txt': {'sat': True, 'unique': False},
    'example7.txt': {'sat': True, 'unique': True},
    'example8.txt': {'sat': False, 'unique': False},
    'example9.txt': {'sat': True, 'unique': False},
    'example10.txt': {'sat': True, 'unique': False},
    'example11.txt': {'sat': True, 'unique': False},
    'example12.txt': {'sat': True, 'unique': False},
    'example13.txt': {'sat': False, 'unique': False},
    'example14.txt': {'sat': False, 'unique': False},
    'example15.txt': {'sat': False, 'unique': False},
    # Large instances
    'example16.txt': {'sat': True, 'unique': False},
    'example17.txt': {'sat': True, 'unique': False},
    'example18.txt': {'sat': True, 'unique': False},
    'example19.txt': {'sat': True, 'unique': False}
}

INSTANCE_GENERATION_ATTEMPTS = 100  # Number of attempts to generate a valid instance

INSTANCE_GENERATION_AUTH_DENSITY_REGULAR = 0.3  # 30% of users authorized for each step
INSTANCE_GENERATION_AUTH_DENSITY_LESS = 0.25  # 25% of users authorized for each step
INSTANCE_GENERATION_AUTH_DENSITY_LESSER = 0.2  # 20% of users authorized for each step
INSTANCE_GENERATION_AUTH_DENSITY_LEAST = 0.15  # 15% of users authorized for each step

INSTANCE_GENERATION_COMPLEX_MIN_LINES_REGULAR = 500  # Regular number of lines for complex instances
INSTANCE_GENERATION_COMPLEX_MAX_LINES_REGULAR = 2000
INSTANCE_GENERATION_COMPLEX_MIN_LINES_LESS = 300
INSTANCE_GENERATION_COMPLEX_MAX_LINES_LESS = 1600
INSTANCE_GENERATION_COMPLEX_MIN_LINES_MORE = 800
INSTANCE_GENERATION_COMPLEX_MAX_LINES_MORE = 3000
