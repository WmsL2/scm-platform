<template>
  <main class="result-page">
    <el-result icon="error" title="403" sub-title="当前账号没有访问该页面的权限">
      <template #extra><el-button type="primary" @click="$router.push('/')">返回工作台</el-button></template>
    </el-result>
  </main>
</template>

<style scoped>
.result-page { display: grid; min-height: 100vh; place-items: center; background: #f5f7fa; }
</style>
