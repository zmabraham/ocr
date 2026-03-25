import { createApp } from 'vue'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import Aura from '@primevue/themes/aura'

import App from './App.vue'
import router from './router'

// PrimeVue components
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Textarea from 'primevue/textarea'
import ProgressBar from 'primevue/progressbar'
import Card from 'primevue/card'
import Panel from 'primevue/panel'
import Dialog from 'primevue/dialog'
import Toast from 'primevue/toast'
import ToastService from 'primevue/toastservice'
import RadioButton from 'primevue/radiobutton'
import Image from 'primevue/image'
import Badge from 'primevue/badge'

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(PrimeVue, {
  theme: {
    preset: Aura,
    options: {
      darkModeSelector: '.dark-mode',
      cssLayer: false
    }
  }
})
app.use(ToastService)

// Register components
app.component('Button', Button)
app.component('InputText', InputText)
app.component('Textarea', Textarea)
app.component('ProgressBar', ProgressBar)
app.component('Card', Card)
app.component('Panel', Panel)
app.component('Dialog', Dialog)
app.component('Toast', Toast)
app.component('RadioButton', RadioButton)
app.component('PvImage', Image)
app.component('Badge', Badge)

app.mount('#app')
