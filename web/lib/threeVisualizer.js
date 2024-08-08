import * as THREE from './three/three.module.js'
import { api } from '../../../scripts/api.js'
import { OrbitControls } from './three/OrbitControls.js'
import { RoomEnvironment } from './three/RoomEnvironment.js'

const visualizer = document.getElementById('visualizer')
const container = document.getElementById('container')
const progressDialog = document.getElementById('progress-dialog')
const progressIndicator = document.getElementById('progress-indicator')

const renderer = new THREE.WebGLRenderer({
  antialias: true,
  extensions: {
    derivatives: true
  }
})
renderer.setPixelRatio(window.devicePixelRatio)
renderer.setSize(window.innerWidth, window.innerHeight)

if (container) container.appendChild(renderer.domElement)

const pmremGenerator = new THREE.PMREMGenerator(renderer)

// scene
const scene = new THREE.Scene()
scene.background = new THREE.Color(0x000000)
scene.environment = pmremGenerator.fromScene(
  new RoomEnvironment(renderer),
  0.04
).texture

const ambientLight = new THREE.AmbientLight(0xffffff)

const camera = new THREE.PerspectiveCamera(
  40,
  window.innerWidth / window.innerHeight,
  0.1,
  1000
)
camera.position.set(0, 0, 10)
const pointLight = new THREE.PointLight(0xffffff, 15)
camera.add(pointLight)

const controls = new OrbitControls(camera, renderer.domElement)
controls.target.set(0, 0, 0)
controls.update()
controls.enablePan = true
controls.enableDamping = true

// Handle window resize event
window.onresize = function () {
  camera.aspect = window.innerWidth / window.innerHeight
  camera.updateProjectionMatrix()

  renderer.setSize(window.innerWidth, window.innerHeight)
}

var lastReferenceImage = ''
var lastDepthMap = ''
var needUpdate = false

function frameUpdate () {
  var referenceImage = visualizer?.getAttribute('reference_image')
  var depthMap = visualizer?.getAttribute('depth_map')
  if (referenceImage == lastReferenceImage && depthMap == lastDepthMap) {
    if (needUpdate) {
      controls.update()
      renderer.render(scene, camera)
    }
    requestAnimationFrame(frameUpdate)
  } else {
    needUpdate = false
    scene.clear()
    if (progressDialog) progressDialog.open = true
    lastReferenceImage = referenceImage
    lastDepthMap = depthMap
    if (lastReferenceImage && lastReferenceImage != 'undefined') {
      // console.log('lastReferenceImage',typeof(lastReferenceImage),lastDepthMap)
      main(JSON.parse(lastReferenceImage), JSON.parse(lastDepthMap))
    }
  }
}

const onProgress = function (xhr) {
  if (xhr.lengthComputable) {
    progressIndicator.value = (xhr.loaded / xhr.total) * 100
  }
}

const onError = function (e) {
  console.error(e)
}

async function main (referenceImageParams, depthMapParams) {
  let referenceTexture, depthTexture
  let imageWidth = 10 // Default width
  let imageHeight = 10 // Default height, will be updated based on the image's aspect ratio
  //   console.log('#referenceImageParams', referenceImageParams)
  if (referenceImageParams?.filename) {
    const referenceImageUrl = api
      .apiURL('/view?' + new URLSearchParams(referenceImageParams))
      .replace(/extensions.*\//, '')
    const referenceImageExt = referenceImageParams.filename.slice(
      referenceImageParams.filename.lastIndexOf('.') + 1
    )

    if (
      referenceImageExt === 'png' ||
      referenceImageExt === 'jpg' ||
      referenceImageExt === 'jpeg'
    ) {
      const referenceImageLoader = new THREE.TextureLoader()
      referenceTexture = await new Promise((resolve, reject) => {
        referenceImageLoader.load(
          referenceImageUrl,
          texture => {
            // Once the image is loaded, update the width and height based on the image's aspect ratio
            imageWidth = 10 // Keep the width as 10
            imageHeight = texture.image.height / (texture.image.width / 10)
            resolve(texture)
          },
          undefined,
          reject
        )
      })
    }
  }

  if (depthMapParams?.filename) {
    const depthMapUrl = api
      .apiURL('/view?' + new URLSearchParams(depthMapParams))
      .replace(/extensions.*\//, '')
    const depthMapExt = depthMapParams.filename.slice(
      depthMapParams.filename.lastIndexOf('.') + 1
    )

    if (
      depthMapExt === 'png' ||
      depthMapExt === 'jpg' ||
      depthMapExt === 'jpeg'
    ) {
      const depthMapLoader = new THREE.TextureLoader()
      depthTexture = await depthMapLoader.loadAsync(depthMapUrl)
    }
  }

  if (referenceTexture && depthTexture) {
    const depthMaterial = new THREE.ShaderMaterial({
      uniforms: {
        referenceTexture: { value: referenceTexture },
        depthTexture: { value: depthTexture },
        depthScale: { value: 5.0 },
        ambientLightColor: { value: new THREE.Color(0.2, 0.2, 0.2) },
        lightPosition: { value: new THREE.Vector3(2, 2, 2) },
        lightColor: { value: new THREE.Color(1, 1, 1) },
        lightIntensity: { value: 1.0 },
        shininess: { value: 30 }
      },
      vertexShader: `
            uniform sampler2D depthTexture;
            uniform float depthScale;
    
            varying vec2 vUv;
            varying float vDepth;
            varying vec3 vNormal;
            varying vec3 vViewPosition;
    
            void main() {
                vUv = uv;
                
                float depth = texture2D(depthTexture, uv).r;
                vec3 displacement = normal * depth * depthScale;
                vec3 displacedPosition = position + displacement;
                
                vec4 worldPosition = modelMatrix * vec4(displacedPosition, 1.0);
                vNormal = normalize(normalMatrix * normal);
                vViewPosition = (viewMatrix * worldPosition).xyz;
                
                gl_Position = projectionMatrix * viewMatrix * worldPosition;
                
                vDepth = depth;
            }
        `,
      fragmentShader: `
            uniform sampler2D referenceTexture;
    
            varying vec2 vUv;
            varying float vDepth;
    
            void main() {
                vec4 referenceColor = texture2D(referenceTexture, vUv);
                
                // Directly use reference color without fog
                gl_FragColor = referenceColor;
            }
        `
    })

    const planeGeometry = new THREE.PlaneGeometry(
      imageWidth,
      imageHeight,
      200,
      200
    )
    const depthMesh = new THREE.Mesh(planeGeometry, depthMaterial)
    scene.add(depthMesh)
  }

  needUpdate = true

  scene.add(ambientLight)
  scene.add(camera)

  progressDialog?.close()

  frameUpdate()
}

document
  .getElementById('screenshotButton')
  ?.addEventListener('click', takeScreenshot)

const sleep = (t = 1000) => {
  return new Promise((res, rej) => {
    setTimeout(() => res(1), t)
  })
}

// 方法：旋转摄像机并拍摄图片 // 每次旋转的角度增量，转换为弧度
async function captureImages (
  totalFrames = 40,
  angleIncrement = THREE.MathUtils.degToRad(0.5)
) {
  // 计算场景中所有物体的中心点
  const box = new THREE.Box3().setFromObject(scene)
  const center = new THREE.Vector3()
  box.getCenter(center)

  // 计算当前相机距离中心点的半径
  const radius = camera.position.distanceTo(center)

  // 存储图片的数组
  let images = []

  // 记录初始相机位置和朝向
  const initialPosition = camera.position.clone()
  const initialTarget = center.clone()

  // 计算当前相机的初始角度
  const initialAngle = Math.atan2(
    camera.position.z - center.z,
    camera.position.x - center.x
  )

  // 起始角度为从当前角度往左旋转 20 度的位置
  const startAngle = initialAngle - (angleIncrement * totalFrames) / 2

  for (let i = 0; i < totalFrames; i++) {
    const angle = startAngle + i * angleIncrement

    // 计算相机的位置
    camera.position.x = center.x + radius * Math.cos(angle)
    camera.position.z = center.z + radius * Math.sin(angle)
    camera.position.y = initialPosition.y // 保持相机高度不变
    camera.lookAt(center) // 相机看向中心点

    // 渲染当前帧
    renderer.render(scene, camera)

    // 将当前帧保存为图片
    const imgData = renderer.domElement.toDataURL('image/png')
    images.push(imgData)

    // 等待一段时间
    await new Promise(resolve => setTimeout(resolve, 500))
  }

  // 恢复相机到初始位置和朝向
  camera.position.copy(initialPosition)
  camera.lookAt(initialTarget)

  return images
}

async function takeScreenshot () {
  // 更新相机的矩阵，以确保其世界矩阵是最新的
  camera.updateMatrixWorld()
  const imgs = await captureImages()

  // 获取当前网页的 URL
  const currentUrl = window.location.href

  // 创建一个 URL 对象
  const url = new URL(currentUrl)

  // 使用 URLSearchParams 获取参数
  const params = new URLSearchParams(url.search)

  // 获取参数 'id' 的值
  const id = params.get('id')

  window.parent.postMessage({ imgs, id }, '*')
}

main()

window.addEventListener('message', event => {
  // 这里可以添加对来源的验证，以确保安全
  // console.log('Message received from parent page:', event.data)
  let { reference_image, depth_map } = event.data
  if (reference_image && depth_map) {
    visualizer?.setAttribute('reference_image', JSON.stringify(reference_image))
    visualizer?.setAttribute('depth_map', JSON.stringify(depth_map))
    frameUpdate()
  }
})
