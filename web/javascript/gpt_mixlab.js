import { app } from '../../../scripts/app.js'
import { ComfyWidgets } from '../../../scripts/widgets.js'

app.registerExtension({
  name: 'Mixlab.GPT.ShowTextForGPT',
  async beforeRegisterNodeDef (nodeType, nodeData, app) {
    if (nodeData.name === 'ShowTextForGPT') {
      function populate (text) {
        text = text.filter(t => t && t?.trim())

        if (this.widgets) {
          // console.log('#ShowTextForGPT',this.widgets)
          // const pos = this.widgets.findIndex(w => w.name === 'text')
          for (let i = 0; i < this.widgets.length; i++) {
            if (this.widgets[i].name == 'show_text')
              this.widgets[i].onRemove?.()
       
          }
          this.widgets.length = 2
        }

        for (let list of text) {
          if (list) {
            // console.log('#####', list)
            const w = ComfyWidgets['STRING'](
              this,
              'show_text',
              ['STRING', { multiline: true }],
              app
            ).widget
            w.inputEl.readOnly = true
            w.inputEl.style.opacity = 0.6

            // w.inputEl.style.display='none'

            try {
              if (typeof list != 'string') {
                let data = JSON.parse(list)
                data = Array.from(data, d => {
                  return {
                    ...d,
                    content: decodeURIComponent(d.content)
                  }
                })
                list = JSON.stringify(data, null, 2)
              }
            } catch (error) {
              console.log(error)
            }

            w.value = list
          }
        }
        // console.log('ShowTextForGPT',this.widgets.length)
        requestAnimationFrame(() => {
          if (this) {
            const sz = this.computeSize()
            if (sz[0] < this.size[0]) {
              sz[0] = this.size[0]
            }
            if (sz[1] < this.size[1]) {
              sz[1] = this.size[1]
            }
            this.onResize?.(sz)
            app.graph.setDirtyCanvas(true, false)
          }
        })
      }

      // When the node is executed we will be sent the input text, display this in the widget
      const onExecuted = nodeType.prototype.onExecuted
      nodeType.prototype.onExecuted = function (message) {
        onExecuted?.apply(this, arguments)
        // console.log('##onExecuted', this, message)
        if (message.text) populate.call(this, message.text)
      }

      const onConfigure = nodeType.prototype.onConfigure
      nodeType.prototype.onConfigure = function () {
        onConfigure?.apply(this, arguments)
        if (this.widgets_values?.length) {
          populate.call(this, this.widgets_values)
        }
      }

      this.serialize_widgets = true //需要保存参数
    }
  }
})
