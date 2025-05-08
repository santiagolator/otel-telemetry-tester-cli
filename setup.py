from setuptools import setup, find_packages

setup(
    name="otel-telemetry-tester-cli",
    version="0.1.2",
    packages=find_packages(include=["otel_telemetry_tester_cli*"]),
    install_requires=[
        'opentelemetry-api>=1.22.0',
        'opentelemetry-sdk>=1.22.0',
        'opentelemetry-exporter-otlp-proto-grpc>=1.22.0',
        'opentelemetry-exporter-otlp-proto-http>=1.22.0',
    ],
    entry_points={
        'console_scripts': [
            'otel-tester=otel_telemetry_tester_cli.cli:main',
        ],
    },
    author="Santiago Lator Arias",
    description="CLI Tool for Testing OpenTelemetry Implementations",
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url="https://github.com/tu-usuario/otel-telemetry-tester-cli",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: System :: Monitoring",
        "Topic :: Utilities"
    ],
    python_requires='>=3.8',
    keywords="opentelemetry testing cli monitoring",
    project_urls={
        "Bug Tracker": "https://github.com/santiagolator/otel-telemetry-tester-cli/issues",
        "Documentation": "https://github.com/santiagolator/otel-telemetry-tester-cli/wiki",
    },
)