import { app } from '../../../scripts/app.js'
// import { api } from '../../../scripts/api.js'
import { ComfyWidgets } from '../../../scripts/widgets.js'
import { $el } from '../../../scripts/ui.js'

app.registerExtension({
  name: 'Mixlab.prompt.ClipInterrogator',
  async beforeRegisterNodeDef (nodeType, nodeData, app) {
    if (nodeData.name === 'ClipInterrogator') {
      function populate (prompts, items) {
        if (this.widgets) {
          for (let i = 0; i < this.widgets.length; i++) {
            if (this.widgets[i].type !== 'combo') this.widgets[i].onRemove?.()
          }
          this.widgets.length = 2
        }

        const w = ComfyWidgets['STRING'](
          this,
          'text',
          ['STRING', { multiline: true }],
          app
        ).widget
        w.inputEl.readOnly = true
        w.inputEl.style.opacity = 0.6

        w.value = prompts.join('\n\n')

        const w2 = ComfyWidgets['STRING'](
          this,
          'text',
          ['STRING', { multiline: true }],
          app
        ).widget
        w2.inputEl.readOnly = true
        w2.inputEl.style.opacity = 0.6

        w2.value = JSON.stringify(items, null, 2)

        console.log('ClipInterrogator',w,w2)
        requestAnimationFrame(() => {
          const sz = this.computeSize()
          if (sz[0] < this.size[0]) {
            sz[0] = this.size[0]
          }
          if (sz[1] < this.size[1]) {
            sz[1] = this.size[1]
          }
          this.onResize?.(sz)
          app.graph.setDirtyCanvas(true, false)
        })
      }

      // When the node is executed we will be sent the input text, display this in the widget
      const onExecuted = nodeType.prototype.onExecuted
      nodeType.prototype.onExecuted = function (message) {
        onExecuted?.apply(this, arguments)
        console.log('##', message)
        populate.call(this, message.prompt, message.analysis)
      }

      this.serialize_widgets = true //需要保存参数
    }
  }
})
