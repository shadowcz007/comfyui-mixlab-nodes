import { app } from '../../../scripts/app.js'
import { $el } from '../../../scripts/ui.js'
import {
  loadExternalScript,
  updateLLMAPIKey,
  get_position_style,
  getLocalData
} from './common.js'

loadExternalScript('/mixlab/app/lib/pickr.min.js')

function hexToRGBA (hexColor) {
  var hex = hexColor.replace('#', '')
  var r = parseInt(hex.substring(0, 2), 16)
  var g = parseInt(hex.substring(2, 4), 16)
  var b = parseInt(hex.substring(4, 6), 16)

  // 获取透明度的十六进制值
  var alphaHex = hex.substring(6)

  // 将透明度的十六进制值转换为十进制值
  var alpha = parseInt(alphaHex, 16) / 255

  return [r, g, b, alpha]
}

app.registerExtension({
  name: 'Mixlab.utils.Color',
  init () {
    $el('link', {
      rel: 'stylesheet',
      href: '/mixlab/app/lib/classic.min.css',
      parent: document.head
    })

    $el('style', {
      textContent: `
      .pickr{
        display: flex;
        justify-content: center;
        align-items: center;
      }
				.pickr .pcr-button {
					width: 56px;
          height: 56px;
          outline: 1px solid white;
				}
				 
			`,
      parent: document.body
    })
  },
  async getCustomWidgets (app) {
    return {
      TCOLOR (node, inputName, inputData, app) {
        // console.log('##node', node)
        const widget = {
          type: inputData[0], // the type, CHEESE
          name: inputName, // the name, slice
          size: [128, 32], // a default size
          draw (ctx, node, width, y) {},
          computeSize (...args) {
            return [128, 32] // a method to compute the current size of the widget
          },
          async serializeValue (nodeId, widgetIndex) {
            // let data = getLocalData('_mixlab_utils_color')
            // let hex = data[node.id] || '#000000'
            let hex = widget.value || '#000000'
            let [r, g, b, a] = hexToRGBA(hex)
            return {
              hex,
              r,
              g,
              b,
              a
            }
          }
        }
        //  widget.something = something;          // maybe adds stuff to it
        node.addCustomWidget(widget) // adds it to the node
        return widget // and returns it.
      }
    }
  },

  async beforeRegisterNodeDef (nodeType, nodeData, app) {
    if (nodeType.comfyClass == 'Color') {
      const orig_nodeCreated = nodeType.prototype.onNodeCreated
      nodeType.prototype.onNodeCreated = function () {
        orig_nodeCreated?.apply(this, arguments)

        // console.log('Color nodeData', this.div)

        const widget = {
          type: 'div',
          name: 'input_color',
          draw (ctx, node, widget_width, y, widget_height) {
            Object.assign(
              this.div.style,
              get_position_style(ctx, widget_width, 44, node.size[1])
            )
            // console.log('draw',y,node.widgets[0].last_y)
          }
        }

        widget.div = $el('div', {})

        document.body.appendChild(widget.div)

        const inputDiv = () => {
          let div = document.createElement('div')
          div.id = `color_picker_${this.id}`
          return div
        }

        let inputColor = inputDiv('_mixlab_utils_color', 'Color', '#000000')

        widget.div.appendChild(inputColor)

        this.addCustomWidget(widget)

        const pickr = Pickr.create({
          el: `#${inputColor.id}`,
          theme: 'classic', // or 'monolith', or 'nano'
          // closeOnScroll: true,
          default: '#000000',
          swatches: [
            'rgba(244, 67, 54, 1)',
            'rgba(233, 30, 99, 0.95)',
            'rgba(156, 39, 176, 0.9)',
            'rgba(103, 58, 183, 0.85)',
            'rgba(63, 81, 181, 0.8)',
            'rgba(33, 150, 243, 0.75)',
            'rgba(3, 169, 244, 0.7)',
            'rgba(0, 188, 212, 0.7)',
            'rgba(0, 150, 136, 0.75)',
            'rgba(76, 175, 80, 0.8)',
            'rgba(139, 195, 74, 0.85)',
            'rgba(205, 220, 57, 0.9)',
            'rgba(255, 235, 59, 0.95)',
            'rgba(255, 193, 7, 1)'
          ],

          components: {
            // Main components
            preview: true,
            opacity: true,
            hue: true,
            // Input / output Options
            interaction: {
              hex: true,
              rgba: true,
              hsla: true,
              hsva: true,
              cmyk: true,
              input: true,
              // clear: true,
              save: true,
              cancel: true
            }
          }
        })

        pickr
          .on('save', (color, instance) => {
            // console.log('Event: "save"', color.toHEXA().toString())
            // let data = getLocalData('_mixlab_utils_color')
            // data[this.id] = color.toHEXA().toString()
            // localStorage.setItem('_mixlab_utils_color', JSON.stringify(data))

            try {
              let tc = this.widgets.filter(w => w.type == 'TCOLOR')[0]
              tc.value = color.toHEXA().toString()
            } catch (error) {}
          })
          .on('cancel', instance => {
            pickr && pickr.hide()
          })
        this.pickr = pickr
        const handleMouseWheel = () => {
          try {
            this.pickr && this.pickr.hide()
          } catch (error) {}
        }

        document.addEventListener('wheel', handleMouseWheel)

        const onRemoved = this.onRemoved
        this.onRemoved = () => {
          inputColor.remove()
          widget.div.remove()

          try {
            this.pickr.destroyAndRemove()
            this.pickr = null
            document.removeEventListener('wheel', handleMouseWheel)
          } catch (error) {
            console.log(error)
          }

          return onRemoved?.()
        }

        this.serialize_widgets = true //需要保存参数
      }
    }
  },
  async loadedGraphNode (node, app) {
    // Fires every time a node is constructed
    // You can modify widgets/add handlers/etc here

    if (node.type === 'Color') {
      try {
        let TCOLOR = node.widgets.filter(w => w.type == 'TCOLOR')[0]

        setTimeout(() => node.pickr.setColor(TCOLOR.value || '#000000'), 1000)
      } catch (error) {}
    }
  }
})

app.registerExtension({
  name: 'Mixlab.utils.TextToNumber',
  async beforeRegisterNodeDef (nodeType, nodeData, app) {
    if (nodeType.comfyClass == 'TextToNumber') {
      const onExecuted = nodeType.prototype.onExecuted
      nodeType.prototype.onExecuted = function (message) {
        onExecuted?.apply(this, arguments)
        const random_number = this.widgets.filter(
          w => w.name === 'random_number'
        )[0]
        if (random_number.value === 'enable') {
          const n = this.widgets.filter(w => w.name === 'number')[0]
          n.value = message.num[0]
        }
        console.log('TextToNumber', random_number.value)
      }
    }
  }
})

const min_max = node => {
  if (node.widgets) {
    const min_value = node.widgets.filter(w => w.name === 'min_value')[0]
    const max_value = node.widgets.filter(w => w.name === 'max_value')[0]

    const number = node.widgets.filter(w => w.name === 'number')[0]
    if (number) {
      number.options.min = min_value.value
      number.options.max = max_value.value

      number.value = Math.min(number.options.max, number.value)
      number.value = Math.max(number.options.min, number.value)
    }

    if (min_value)
      min_value.callback = e => {
        number.options.min = e
        number.value = e
      }
    if (max_value)
      max_value.callback = e => {
        number.options.max = e
        number.value = e
      }
  }
}

app.registerExtension({
  name: 'Mixlab.utils.FloatSlider',
  async beforeRegisterNodeDef (nodeType, nodeData, app) {
    if (nodeType.comfyClass == 'FloatSlider') {
      const orig_nodeCreated = nodeType.prototype.onNodeCreated
      nodeType.prototype.onNodeCreated = function () {
        orig_nodeCreated?.apply(this, arguments)
        min_max(this)
      }
    }
  },
  async loadedGraphNode (node, app) {
    if (node.type === 'FloatSlider') {
      min_max(node)
    }
  }
})
app.registerExtension({
  name: 'Mixlab.utils.IntNumber',
  async beforeRegisterNodeDef (nodeType, nodeData, app) {
    if (nodeType.comfyClass == 'IntNumber') {
      const orig_nodeCreated = nodeType.prototype.onNodeCreated
      nodeType.prototype.onNodeCreated = function () {
        orig_nodeCreated?.apply(this, arguments)
        min_max(this)
      }
    }
  },
  async loadedGraphNode (node, app) {
    if (node.type === 'IntNumber') {
      min_max(node)
    }
  }
})

app.registerExtension({
  name: 'Mixlab.utils.TESTNODE_',
  async beforeRegisterNodeDef (nodeType, nodeData, app) {
    if (nodeType.comfyClass == 'TESTNODE_') {
      const onExecuted = nodeType.prototype.onExecuted
      nodeType.prototype.onExecuted = function (message) {
        onExecuted?.apply(this, arguments)
        console.log('##', message)
      }
    }
  }
})

app.registerExtension({
  name: 'Mixlab.utils.KeyInput',
  init () {},
  async getCustomWidgets (app) {
    return {
      KEY (node, inputName, inputData, app) {
        // console.log('##node', node)
        const widget = {
          type: inputData[0], // the type, CHEESE
          name: inputName, // the name, slice
          size: [128, 24], // a default size
          draw (ctx, node, width, y) {},
          computeSize (...args) {
            return [128, 32] // a method to compute the current size of the widget
          },
          async serializeValue (nodeId, widgetIndex) {
            let data = getLocalData('_mixlab_llm_api_key')
            return data[node.id] || 'by Mixlab'
          }
        }
        //  widget.something = something;          // maybe adds stuff to it
        node.addCustomWidget(widget) // adds it to the node
        return widget // and returns it.
      }
    }
  },

  async beforeRegisterNodeDef (nodeType, nodeData, app) {
    if (nodeType.comfyClass == 'KeyInput') {
      const orig_nodeCreated = nodeType.prototype.onNodeCreated
      nodeType.prototype.onNodeCreated = function () {
        orig_nodeCreated?.apply(this, arguments)

        const rowHeight = this.rowHeight
        const widget = {
          type: 'div',
          name: 'input_key',
          draw (ctx, node, widget_width, y, widget_height) {
            Object.assign(
              this.div.style,
              get_position_style(ctx, widget_width, y, node.size[1])
            )
          }
        }

        widget.div = $el('div', {})

        document.body.appendChild(widget.div)

        const inputDiv = (key, placeholder) => {
          let div = document.createElement('div')
          div.style = `
          display: flex;
          align-items: center; 
          margin: 6px 8px;
          margin-top:0px;
          height:44px;
          width:220px; 
          `

          const ip = document.createElement('input')
          ip.type = 'password'
          ip.className = `${'comfy-multiline-input'} ${placeholder}`

          ip.placeholder = placeholder
          // ip.value = placeholder

          ip.style = `margin-left:8px;
            outline: none;
            border: none;
            padding:12px;
            width: 100%;
            `

          div.appendChild(ip)

          ip.addEventListener('change', () => {
            let data = getLocalData(key)
            data[this.id] = ip.value.trim()
            localStorage.setItem(key, JSON.stringify(data))
            updateLLMAPIKey(data[this.id])
          })

          return div
        }

        let inputKey = inputDiv('_mixlab_llm_api_key', 'Key')

        widget.div.appendChild(inputKey)

        this.addCustomWidget(widget)

        const onRemoved = this.onRemoved
        this.onRemoved = () => {
          inputKey.remove()
          widget.div.remove()
          return onRemoved?.()
        }

        // const processMouseWheel=app.canvas.processMouseWheel
        // app.canvas.processMouseWheel=()=>{
        //   console.log(app.canvas.ds.scale)
        //   return processMouseWheel?.()
        // }

        this.serialize_widgets = true //需要保存参数
      }
    }
  },
  async loadedGraphNode (node, app) {
    if (node.type === 'KeyInput') {
      let widget = node.widgets.filter(w => w.div)[0]

      let apiKey = getLocalData('_mixlab_llm_api_key')

      let id = node.id
      if (widget.div.querySelector('.Key'))
        widget.div.querySelector('.Key').value = apiKey[id] || 'by Mixlab'

      if (apiKey[id]) updateLLMAPIKey(apiKey[id])
    }
  },
  nodeCreated (node, app) {
    //数据延迟？？
    setTimeout(() => {
      // console.log('#LoadImagesToBatch', node.type)
      if (node.type === 'KeyInput') {
        let widget = node.widgets.filter(w => w.div)[0]

        let apiKey = getLocalData('_mixlab_llm_api_key')

        let id = node.id

        if (widget.div.querySelector('.Key'))
          widget.div.querySelector('.Key').value = apiKey[id] || 'by Mixlab'

        if (apiKey[id]) updateLLMAPIKey(apiKey[id])
      }
    }, 1000)
  }
})
