import os
import jpype
import jpype.imports


def init_jvm():
    """Initialize JVM if not already started"""
    if not jpype.isJVMStarted():
        # Look for jar in assets folder
        jarpath = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "sat4j-pb.jar")
        if not os.path.exists(jarpath):
            raise FileNotFoundError(
                "sat4j-pb.jar not found. Please download it from sat4j.org "
                "and place it in the assets directory."
            )
        jpype.startJVM(classpath=[jarpath])
