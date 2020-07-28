#include <jni.h>
#include <stdio.h>
#include <dlfcn.h>

/* JNI Functions */

JNIEXPORT void JNICALL Java_probe_RustMMTkProbe_begin_1native
  (JNIEnv *env, jobject o, jstring benchmark, jint iteration, jboolean warmup, jlong thread_id) {
  void* handle = dlopen(NULL, RTLD_LAZY);
  void (*harness_begin)(jlong) = dlsym(handle, "harness_begin");
  (*harness_begin)(thread_id);
}

JNIEXPORT void JNICALL Java_probe_RustMMTkProbe_end_1native
  (JNIEnv *env, jobject o, jstring benchmark, jint iteration, jboolean warmup, jlong thread_id) {
  void* handle = dlopen(NULL, RTLD_LAZY);
  void (*harness_end)(jlong) = dlsym(handle, "harness_end");
  (*harness_end)(thread_id);
}
