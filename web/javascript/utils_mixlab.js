import { app } from '../../../scripts/app.js'
import { api } from '../../../scripts/api.js'
import { ComfyWidgets } from '../../../scripts/widgets.js'
import { $el } from '../../../scripts/ui.js'
import { addValueControlWidget } from '../../../scripts/widgets.js'

const getLocalData = key => {
  let data = {}
  try {
    data = JSON.parse(localStorage.getItem(key)) || {}
  } catch (error) {
    return {}
  }
  return data
}
function get_position_style (ctx, widget_width, y, node_height) {
  const MARGIN = 4 // the margin around the html element

  /* Create a transform that deals with all the scrolling and zooming */
  const elRect = ctx.canvas.getBoundingClientRect()
  const transform = new DOMMatrix()
    .scaleSelf(
      elRect.width / ctx.canvas.width,
      elRect.height / ctx.canvas.height
    )
    .multiplySelf(ctx.getTransform())
    .translateSelf(MARGIN, MARGIN + y)

  return {
    transformOrigin: '0 0',
    transform: transform,
    left: `0`,
    top: `0`,
    cursor: 'pointer',
    position: 'absolute',
    maxWidth: `${widget_width - MARGIN * 2}px`,
    // maxHeight: `${node_height - MARGIN * 2}px`, // we're assuming we have the whole height of the node
    width: `${widget_width - MARGIN * 2}px`,
    // height: `${node_height * 0.3 - MARGIN * 2}px`,
    // background: '#EEEEEE',
    display: 'flex',
    flexDirection: 'column',
    // alignItems: 'center',
    justifyContent: 'space-around'
  }
}

function hexToRGBA (hexColor) {
  var hex = hexColor.replace('#', '')
  var r = parseInt(hex.substring(0, 2), 16)
  var g = parseInt(hex.substring(2, 4), 16)
  var b = parseInt(hex.substring(4, 6), 16)

  // 获取透明度的十六进制值
  var alphaHex = hex.substring(6)

  // 将透明度的十六进制值转换为十进制值
  var alpha = parseInt(alphaHex, 16) / 255

  return [r,g,b,alpha]
}

app.registerExtension({
  name: 'Mixlab.utils.Color',
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
            let data = getLocalData('_mixlab_utils_color');
            let hex=data[node.id] || '#000000'
            let [r,g,b,a]=hexToRGBA(hex)
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

        console.log('Color nodeData', this.widgets)

        const widget = {
          type: 'div',
          name: 'input_color',
          draw (ctx, node, widget_width, y, widget_height) {
            Object.assign(
              this.div.style,
              get_position_style(ctx, widget_width, 44, node.size[1])
            )
          }
        }

        widget.div = $el('div', {})

        document.body.appendChild(widget.div)

        const inputDiv = (key, placeholder, value) => {
          let div = document.createElement('div')
          const ip = document.createElement('input')
          ip.type = 'color'
          ip.className = `${'comfy-multiline-input'} ${placeholder}`
          div.style = `display: flex;
            align-items: center; 
            margin: 6px 8px;
            margin-top: 0;`
          ip.placeholder = placeholder
          ip.value = value

          ip.style = `outline: none;
            border: none;
            padding: 4px;
            width: 70%;cursor: pointer;
            height: 32px;`
          const label = document.createElement('label')
          label.style = 'font-size: 10px;min-width:32px'
          label.innerText = placeholder
          div.appendChild(label)
          div.appendChild(ip)

          ip.addEventListener('change', () => {
            let data = getLocalData(key)
            data[this.id] = ip.value.trim()
            localStorage.setItem(key, JSON.stringify(data))
            // console.log(this.id, ip.value.trim())
          })
          return div
        }

        let inputColor = inputDiv('_mixlab_utils_color', 'Color', '#000000')

        widget.div.appendChild(inputColor)

        this.addCustomWidget(widget)

        const onRemoved = this.onRemoved
        this.onRemoved = () => {
          inputColor.remove()
          widget.div.remove()
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
      let widget = node.widgets.filter(w => w.div)[0]

      let data = getLocalData('_mixlab_utils_color')

      let id = node.id

      widget.div.querySelector('.Color').value = data[id] || '#000000'
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
