// The Android app module needs Google's Maven (Android Gradle Plugin, androidx). It is only included when
// -PwithApp is passed, so `gradle :core:test` works on machines that cannot reach Google's repositories.
val withApp: Boolean = providers.gradleProperty("withApp").isPresent

pluginManagement {
    repositories {
        gradlePluginPortal()
        mavenCentral()
    }
}

dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.PREFER_SETTINGS)
    repositories {
        mavenCentral()
        // androidx (core-ktx, work-runtime) is published only on Google's Maven; PREFER_SETTINGS ignores
        // project-level repositories, so it must be listed here - and only when :app is included.
        if (withApp) google()
    }
}

rootProject.name = "commscap-android"

include(":core")
if (withApp) {
    include(":app")
}
