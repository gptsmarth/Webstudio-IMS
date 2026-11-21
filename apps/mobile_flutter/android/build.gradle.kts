allprojects {
    repositories {
        google()
        mavenCentral()
    }
}

val newBuildDir: Directory =
    rootProject.layout.buildDirectory
        .dir("../../build")
        .get()
rootProject.layout.buildDirectory.value(newBuildDir)

subprojects {
    val newSubprojectBuildDir: Directory = newBuildDir.dir(project.name)
    project.layout.buildDirectory.value(newSubprojectBuildDir)

    if (name == "camera_android_camerax") {
        plugins.withId("com.android.library") {
            // CameraX 1.5.3 provides this at runtime, but javac needs it for SurfaceRequest.
            dependencies.add("compileOnly", "androidx.concurrent:concurrent-futures:1.1.0")
        }
    }
}

// Flutter plugins ship with older compileSdk values; force a consistent SDK for AGP 9.
subprojects {
    afterEvaluate {
        extensions.findByType(com.android.build.gradle.LibraryExtension::class.java)?.apply {
            compileSdk = 36
        }
    }
}

tasks.register<Delete>("clean") {
    delete(rootProject.layout.buildDirectory)
}
