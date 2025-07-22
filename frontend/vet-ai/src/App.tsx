import { ConfigProvider, Divider, Image, Segmented, Tag } from "antd"
import { useState } from "react"
import "./app.css"
import NameTitle from "./components/common/NameTitle"
import VetCard from "./components/common/VetCard"
import VetSubCard from "./components/common/VetSubCard"
import { CiDot02S, CiDot05Xl } from "./components/icons"

function App() {
  const [state, setState] = useState<string>("外部图")
  /*--------------------------------------- info ------------------------------------------*/
  const weight = "25kg" // 假设体重为5kg
  const name = "小白" // 假设宠物名字为小白
  const age = "2岁3个月" // 假设宠物年龄为2岁3个月
  const species = "金毛巡回犬" // 假设宠物品种为金毛巡回犬
  const gender = "雄性" // 假设宠物性别为雄性
  const refer = "已完成全面疫苗接种、定期驱虫及绝育，但当前存在食欲减精袖茅酶欢俑乃轻庭脱水的核伴随咳症犬已己光与触摸全身紧张反应;其他指标如疼痛评分、皮肤被毛柔顺度、骨骼行动能力、尿液状态及既往病史均为正常，未发现显著的眼周异常、泌尿道问题、瘙痒或肌肉丢失。"
  const pics = [
    "https://tc.z.wiki/autoupload/f/m_blQly9PSfGE1G7DOmbEQoyAJua5RorjteE-UQNnhGyl5f0KlZfm6UsKj-HyTuv/20250722/2FMg/1179X1453/image.png",
    "https://tc.z.wiki/autoupload/f/m_blQly9PSfGE1G7DOmbEQoyAJua5RorjteE-UQNnhGyl5f0KlZfm6UsKj-HyTuv/20250722/WSY7/736X736/image.png",
    "https://tc.z.wiki/autoupload/f/m_blQly9PSfGE1G7DOmbEQoyAJua5RorjteE-UQNnhGyl5f0KlZfm6UsKj-HyTuv/20250722/qxD8/736X751/image.png",
    "https://tc.z.wiki/autoupload/f/m_blQly9PSfGE1G7DOmbEQoyAJua5RorjteE-UQNnhGyl5f0KlZfm6UsKj-HyTuv/20250722/IKyK/721X732/image.png",
    "https://tc.z.wiki/autoupload/f/m_blQly9PSfGE1G7DOmbEQoyAJua5RorjteE-UQNnhGyl5f0KlZfm6UsKj-HyTuv/20250722/QEsV/474X498/image.png",
    "https://tc.z.wiki/autoupload/f/m_blQly9PSfGE1G7DOmbEQoyAJua5RorjteE-UQNnhGyl5f0KlZfm6UsKj-HyTuv/20250722/pbWQ/754X683/image.png"
  ]

  return (
    <ConfigProvider
      theme={{
        components: {
          Segmented: {
            /* 这里是你的组件 token */
            itemActiveBg: "#8093f3", // 设置选中项的背景色
            itemSelectedBg: "#8093f3", // 设置选中项的背景色
            itemSelectedColor: "#fff", // 设置选中项的文字颜色
          },
        },
      }}
    >
      <article className="w-screen h-screen bg-gradient-to-b from-blue-200 via-blue-50 to-white text-black">
        <header className="w-full flex justify-center items-center text-xl font-bold text-gray-800 p-4 h-[3.8rem]">
          AI 问诊报告
        </header>

        <div className=" w-full h-[calc(100vh-3.8rem)] overflow-y-auto px-3 pb-5" >

          {/* /*--------------------------------------- 基本信息 ------------------------------------------*/}
          <section className="w-full h-24 bg-white rounded-lg flex items-center justify-start">
            <img src="https://tc.z.wiki/autoupload/f/m_blQly9PSfGE1G7DOmbEQoyAJua5RorjteE-UQNnhGyl5f0KlZfm6UsKj-HyTuv/20250722/vG07/735X709/image.png" alt=""
              className="h-18 px-5"
            />

            <div className="flex flex-col justify-between h-full py-3">
              <span className="text-gray-800 text-lg font-semibold">{name}</span>
              <span className="text-gray-500 text-sm">
                {species} <CiDot02S className="inline-block" />
                {age} <CiDot02S className="inline-block" />
                {gender}
              </span>
              <span className="text-gray-500 text-sm">
                <CiDot05Xl className="inline-block w-4 h-4 text-green-500 text-2xl" />
                体重：{weight}</span>
            </div>
          </section>
          {/* /*--------------------------------------- 报告描述 ------------------------------------------*/}
          <NameTitle title="报告描述" />

          <section className="w-full bg-white rounded-lg  px-5 py-3">
            <h3 className="font-bold block">基本信息</h3>

            <div className="flex mt-2">
              <span>报告日期：</span>
              <span className="flex-1 flex justify-end">2025年4月1日 14:00</span>
            </div>

            <div className="flex mt-2">
              <span>报告等级：</span>
              <span className="text-green-500 flex-1 flex justify-end">正常</span>
            </div>


            <Divider />
            <div className="flex mt-2">
              <span>病情主诉：</span>
              <p className="flex-1 px-2">反复咳嗽、咳痰伴气促2周，加重3天。自服止咳药效果不佳，近日出现发热，体温最高38.5°C，无胸痛、咯血，无夜间阵发性呼吸困难。</p>
            </div>
          </section>

          {/* /*--------------------------------------- 诊断依据 ------------------------------------------*/}
          <VetCard title="诊断依据" >
            <h3 className="my-2 font-bold text-[#8093f3]">AI 检查表勾选情况</h3>
            <p>{refer}</p>
            <h3 className="my-2 font-bold text-[#8093f3]">诊断图片</h3>
            <div className="flex items-center justify-start flex-wrap gap-1">
              {pics.map((pic, index) => (
                <Image key={index} src={pic} alt={`诊断图片 ${index + 1}`} width={96} height={96} />
              ))}
            </div>
            <h3 className="my-2 font-bold text-[#8093f3]">基础信息</h3>
            <div className="flex items-center text-sm justify-between bg-gray-50 rounded-lg px-3 py-2">
              <span>
                体温:38°C
              </span>
              <Divider type="vertical" className="mx-2" />
              <span>
                心率:100次/分
              </span>
              <Divider type="vertical" className="mx-2" />
              <span>
                呼吸:25次/分
              </span>
            </div>
            <h3 className="my-2 font-bold text-[#8093f3]">宠物结构图</h3>

            <Segmented<string>
              className="w-full"
              options={['外部图', '内部图', '骨骼图']}
              onChange={(value) => {
                console.log(value); // string
                setState(value) // 更新状态
              }}
            />

            <img className={` ${state === '外部图' ? 'block' : 'hidden'}`} src="https://tc.z.wiki/autoupload/f/m_blQly9PSfGE1G7DOmbEQoyAJua5RorjteE-UQNnhGyl5f0KlZfm6UsKj-HyTuv/20250723/PZGn/700X530/image.png" alt="" />
            <img className={` ${state === '内部图' ? 'block' : 'hidden'}`} src="https://tc.z.wiki/autoupload/f/m_blQly9PSfGE1G7DOmbEQoyAJua5RorjteE-UQNnhGyl5f0KlZfm6UsKj-HyTuv/20250723/4W9t/450X450/image.png" alt="" />
            <img className={` ${state === '骨骼图' ? 'block' : 'hidden'}`} src="https://tc.z.wiki/autoupload/f/m_blQly9PSfGE1G7DOmbEQoyAJua5RorjteE-UQNnhGyl5f0KlZfm6UsKj-HyTuv/20250723/0jIl/diagram-dogs-body-with-organs-labeled-as-organs-body_1287512-49095.avif" alt="" />


          </VetCard>
          {/* /*--------------------------------------- 诊断 ------------------------------------------*/}

          <div className="w-full flex items-center justify-center my-5">
            <Segmented<string>
              options={['西医诊断', '中医诊断']}
              onChange={(value) => {
                console.log(value); // string
              }}
            />
          </div>

          <VetCard title="诊断鉴别" >
            <div className="">
              <span className="text-2xl font-bold mr-2">{"牙周炎"}</span>
              <Tag color="#f00" className="inline-block">
                概率极高
              </Tag>
            </div>
            <p className="my-2">
              {`根据AI诊断依据，Max(雪纳瑞，公，5岁)表现出食欲下降、口水增多、口臭、牙龈红肿、牙结石覆盖大部分牙齿等症状，且精神状态较差，高度怀疑为牙周炎。牙周是犬常见的口腔疾病，由牙菌斑和牙结石引起，导致牙龈炎症、牙周组织破坏，严重时可引起牙齿松动脱落，甚至影响全身健
康。`}
            </p>
            <Tag className="black my-2" color="#8093f3">
              初步治疗
            </Tag>
            <VetSubCard medicine="氯已定漱口水">
              <span>口展服|12.5mg/kg 每天2次</span>
              <p className="mt-1">
                【兽用非处方药】使用时避免吞咽。使用棉签或纱布取稀释后的漱口水，轻轻擦拭Max的牙龈和牙齿表面。如果Max抗拒，可以尝试使用宠物专用口腔清洁凝胶。
              </p>
            </VetSubCard>
            <Tag className="black my-2" color="#f1b680">
              持续治疗
            </Tag>
            <VetSubCard medicine="氯已定漱口水">
              <span>口展服|12.5mg/kg 每天2次</span>
              <p className="mt-1">
                【兽用非处方药】使用时避免吞咽。使用棉签或纱布取稀释后的漱口水，轻轻擦拭Max的牙龈和牙齿表面。如果Max抗拒，可以尝试使用宠物专用口腔清洁凝胶。
              </p>
            </VetSubCard>
            <Tag className="black my-2" color="#dd524c">
              重度治疗
            </Tag>
            <VetSubCard medicine="氯已定漱口水">
              <span>口展服|12.5mg/kg 每天2次</span>
              <p className="mt-1">
                【兽用非处方药】使用时避免吞咽。使用棉签或纱布取稀释后的漱口水，轻轻擦拭Max的牙龈和牙齿表面。如果Max抗拒，可以尝试使用宠物专用口腔清洁凝胶。
              </p>
            </VetSubCard>
          </VetCard>
          {/* /*--------------------------------------- end ------------------------------------------*/}
          <section className="w-full bg-[#8093f3] rounded-lg  px-5 py-3 mt-2">
            <p className="text-center text-white">
              <b className="font-bold">
                用户悉知
              </b>
              <br />
              中西医诊断需结合患宠具体情况，仅供参考，实际医疗诊断需以专业医疗机构检查和医师判断为准。
              <br />
              <b>
                如需要更详细的用药及护理建议，可联系在线医生，定制线上有针对性的治疗方案。
              </b>
            </p>
          </section>
        </div >

      </article >
    </ConfigProvider>

  )
}

export default App
