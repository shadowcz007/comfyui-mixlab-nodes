import { app } from '../../../scripts/app.js'
// import { api } from '../../../scripts/api.js'
import { ComfyWidgets } from '../../../scripts/widgets.js'
import { $el } from '../../../scripts/ui.js'

function getRandomElements (arr, num) {
  var result = []
  var len = arr.length

  for (var i = 0; i < num; i++) {
    var randomIndex = Math.floor(Math.random() * len)
    result.push(arr[randomIndex])
  }

  return result
}

const createPrompt = (node, prompts, items, sample) => {
  const w = ComfyWidgets['STRING'](
    node,
    'text',
    ['STRING', { multiline: true }],
    app
  ).widget
  w.inputEl.readOnly = true
  w.inputEl.style.opacity = 0.6

  w.value = typeof prompts === 'string' ? prompts : prompts.join('\n\n')

  const w2 = ComfyWidgets['STRING'](
    node,
    'text',
    ['STRING', { multiline: true }],
    app
  ).widget
  w2.inputEl.readOnly = true
  w2.inputEl.style.opacity = 0.6

  w2.value = typeof items === 'string' ? items : JSON.stringify(items, null, 2)

  const w3 = ComfyWidgets['STRING'](
    node,
    'text',
    ['STRING', { multiline: true }],
    app
  ).widget
  w3.inputEl.readOnly = true
  w3.inputEl.style.opacity = 0.6
  w3.value = typeof sample === 'string' ? sample : sample.join('\n\n')
}

app.registerExtension({
  name: 'Mixlab.prompt.ClipInterrogator',
  async beforeRegisterNodeDef (nodeType, nodeData, app) {
    if (nodeData.name === 'ClipInterrogator') {
      function populate (prompts, items, random_samples) {
        if (this.widgets) {
          for (let i = 0; i < this.widgets.length; i++) {
            if (this.widgets[i].type !== 'combo') this.widgets[i].onRemove?.()
          }
          this.widgets.length = 2
        }

        createPrompt(this, prompts, items, random_samples)

        // console.log('ClipInterrogator', w, w2)
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
        // console.log('##', message)
        populate.call(
          this,
          message.prompt,
          message.analysis,
          message.random_samples
        )
      }

      this.serialize_widgets = true //需要保存参数
    }
  },
  async loadedGraphNode (node, app) {
    // Fires every time a node is constructed
    // You can modify widgets/add handlers/etc here

    if (node.type === 'ClipInterrogator') {
      try {
        
        let widgets_values = node.widgets_values
        console.log(widgets_values )
        try {
          if (widgets_values[2] && widgets_values[3] && widgets_values[4])
            createPrompt(
              node,
              widgets_values[2],
              widgets_values[3],
              widgets_values[4]
            )
        } catch (error) {
          console.log(error)
        }
      } catch (error) {}
    }
  }
})
