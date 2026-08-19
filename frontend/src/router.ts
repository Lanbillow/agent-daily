import { createRouter, createWebHashHistory } from 'vue-router'
import Dashboard from './views/Dashboard.vue'
import Jobs from './views/Jobs.vue'
import Artifacts from './views/Artifacts.vue'
import Config from './views/Config.vue'
import Logs from './views/Logs.vue'
import Models from './views/Models.vue'
import Runs from './views/Runs.vue'
import Scheduler from './views/Scheduler.vue'

export const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    { path: '/', component: Dashboard },
    { path: '/jobs', component: Jobs },
    { path: '/artifacts', component: Artifacts },
    { path: '/runs', component: Runs },
    { path: '/models', component: Models },
    { path: '/scheduler', component: Scheduler },
    { path: '/logs', component: Logs },
    { path: '/config', component: Config },
  ],
})
