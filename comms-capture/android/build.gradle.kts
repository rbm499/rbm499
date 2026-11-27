// Root build: plugin versions live here so every module shares one classloader.
// The Android Gradle Plugin comes from Google's Maven, which is only added (and only resolved) with -PwithApp.
buildscript {
    if (project.hasProperty("withApp")) {
        repositories {
            google()
            mavenCentral()
        }
        dependencies {
            classpath("com.android.tools.build:gradle:8.7.3")
        }
    }
}

plugins {
    kotlin("jvm") version "2.0.21" apply false
    kotlin("android") version "2.0.21" apply false
}
