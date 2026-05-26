import './app.css'
import App from './App.svelte'
import { installAppAlert } from './app-alert.js'

installAppAlert()

const app = new App({
  target: document.getElementById('app'),
})

export default app
