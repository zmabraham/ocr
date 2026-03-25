<template>
  <div class="app-container">
    <Toast />
    <header class="app-header">
      <h1>Hebrew OCR Post-Processor</h1>
      <nav class="app-nav">
        <router-link to="/">Upload</router-link>
        <router-link to="/documents">Documents</router-link>
        <router-link to="/review">Review</router-link>
      </nav>
    </header>
    <main class="app-main">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'

onMounted(() => {
  document.documentElement.lang = 'he'
  document.documentElement.dir = 'rtl'
})
</script>

<style scoped>
.app-container {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.app-header {
  background: #1e3a5f;
  color: white;
  padding: 1rem 2rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.app-header h1 {
  margin: 0;
  font-size: 1.5rem;
}

.app-nav {
  display: flex;
  gap: 1.5rem;
}

.app-nav a {
  color: white;
  text-decoration: none;
  padding: 0.5rem 1rem;
  border-radius: 4px;
  transition: background 0.2s;
}

.app-nav a:hover,
.app-nav a.router-link-active {
  background: rgba(255, 255, 255, 0.2);
}

.app-main {
  flex: 1;
  padding: 2rem;
}
</style>
