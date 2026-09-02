pluginManagement {
    repositories {
        // Official Google CDN endpoint; usable where dl.google.com is unavailable.
        maven("https://redirector.gvt1.com/edgedl/android/maven2/")
        google()
        mavenCentral()
        gradlePluginPortal()
        maven("https://maven.neshan.org/artifactory/public-maven")
    }
}
dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        // Keep Android dependencies buildable on the same restricted networks.
        maven("https://redirector.gvt1.com/edgedl/android/maven2/")
        google()
        mavenCentral()
        maven("https://maven.neshan.org/artifactory/public-maven")
    }
}
rootProject.name = "SellerNavigator"
include(":app")
