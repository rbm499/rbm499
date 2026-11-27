import org.jetbrains.kotlin.gradle.dsl.JvmTarget

// Pure Kotlin/JVM module: no Android, no JSON library. Shared decision logic that the app and the tests use.
plugins {
    kotlin("jvm")
}

java {
    sourceCompatibility = JavaVersion.VERSION_17
    targetCompatibility = JavaVersion.VERSION_17
}

kotlin {
    compilerOptions {
        jvmTarget.set(JvmTarget.JVM_17)
    }
}

dependencies {
    testImplementation(platform("org.junit:junit-bom:5.10.3"))
    testImplementation("org.junit.jupiter:junit-jupiter")
    testRuntimeOnly("org.junit.platform:junit-platform-launcher")
    // JSON parsing for the shared test vectors only (TEST code); main code never touches JSON.
    testImplementation("org.json:json:20240303")
}

val vectorsDir: String = providers.gradleProperty("vectors.dir")
    .orElse(rootProject.layout.projectDirectory.dir("../shared/vectors").asFile.absolutePath)
    .get()

tasks.test {
    useJUnitPlatform()
    systemProperty("vectors.dir", vectorsDir)
    inputs.dir(vectorsDir)
    testLogging {
        events("failed", "skipped")
        showStandardStreams = false
        exceptionFormat = org.gradle.api.tasks.testing.logging.TestExceptionFormat.FULL
    }
}
