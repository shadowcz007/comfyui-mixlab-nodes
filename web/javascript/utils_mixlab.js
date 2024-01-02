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

  return [r, g, b, alpha]
}

app.registerExtension({
  name: 'Mixlab.utils.Color',
  init () {
    $el('link', {
      rel: 'stylesheet',
      href: '/extensions/comfyui-mixlab-nodes/lib/classic.min.css',
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

        // console.log('Color nodeData', this.widgets)

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
          default:'#000000',
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
