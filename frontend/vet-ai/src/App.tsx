import { ConfigProvider, Divider, Image, Segmented, Tag } from "antd"
import { useState } from "react"
import "./app.css"
import NameTitle from "./components/common/NameTitle"
import VetCard from "./components/common/VetCard"
import VetSubCard from "./components/common/VetSubCard"
import { CiDot02S, CiDot05Xl } from "./components/icons"

function App() {
  const [state, setState] = useState<string>("外部图")
  const [doctor, setDoctor] = useState<"西医" | "中医">("西医")
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
              <p className="flex-1 px-2">姓名凯凯，为一雌性金毛犬，:现年7岁，体重26 kg。送来时主诉:最近几天精神不好，食欲不振，有浓鼻液、浓眼屎，打喷嚏，拉稀。</p>
            </div>
          </section>

          {/* /*--------------------------------------- 诊断依据 ------------------------------------------*/}
          <VetCard title="诊断依据" >
            <h3 className="my-2 font-bold text-[#8093f3]">AI 检查表勾选情况</h3>
            <p>{refer}</p>
            <h3 className="my-2 font-bold text-[#8093f3]">诊断图片</h3>
            <div className="flex items-center justify-center flex-wrap gap-1">
              <Image.PreviewGroup
                items={pics}
              >
                {pics.map((pic, index) => (
                  <Image key={index} src={pic} alt={`诊断图片 ${index + 1}`} width={96} height={96} />
                ))}
              </Image.PreviewGroup>


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

            <img className={` ${state === '外部图' ? 'block' : 'hidden'}`} src="https://tc.z.wiki/autoupload/f/m_blQly9PSfGE1G7DOmbEQoyAJua5RorjteE-UQNnhGyl5f0KlZfm6UsKj-HyTuv/20250723/7f1I/640X560/image.png" alt="" />
            <img className={` ${state === '骨骼图' ? 'block' : 'hidden'}`} src="https://tc.z.wiki/autoupload/f/m_blQly9PSfGE1G7DOmbEQoyAJua5RorjteE-UQNnhGyl5f0KlZfm6UsKj-HyTuv/20250723/4W9t/450X450/image.png" alt="" />
            <img className={` ${state === '内部图' ? 'block' : 'hidden'}`} src="https://tc.z.wiki/autoupload/f/m_blQly9PSfGE1G7DOmbEQoyAJua5RorjteE-UQNnhGyl5f0KlZfm6UsKj-HyTuv/20250723/0jIl/diagram-dogs-body-with-organs-labeled-as-organs-body_1287512-49095.avif" alt="" />


          </VetCard>
          {/* /*--------------------------------------- 诊断 ------------------------------------------*/}

          <div className="w-full flex items-center justify-center my-5">
            <Segmented<string>
              options={['西医诊断', '中医诊断']}
              onChange={(value) => {
                console.log(value); // string
                if (value === '西医诊断') {
                  setDoctor("西医");

                } else {
                  setDoctor("中医");
                }
              }}
            />
          </div>

          {
            doctor === "西医" && mock_data.data.map(item => {
              return (
                <VetCard title="诊断鉴别" key={item.disease}>
                  <div className="mt-5 flex items-center justify-start flex-wrap">
                    <span className="text-2xl font-bold mr-2 text-wrap whitespace-break-spaces">{item.disease}</span>
                    {item.p >= 0.8 && <Tag color="#f00" className="inline-block">
                      概率极高
                    </Tag>}
                    {item.p >= 0.5 && <Tag color="#ff9900" className="inline-block">
                      概率较高
                    </Tag>}
                    {item.p < 0.5 && <Tag color="#030" className="inline-block">
                      概率较低
                    </Tag>}
                  </div>
                  <p className="my-3">
                    {`根据AI诊断依据，${item.description}。`}
                  </p>

                  <VetSubCard medicine={
                    <Tag className="black my-2" color="#8093f3">
                      {item.base_medicine ? item.base_medicine : "初步治疗建议："}
                    </Tag>
                  }>
                    {item.base_medicine_usage && <p className="mt-1 text-[#8093f3] font-bold text-sm">
                      {item.base_medicine_usage}
                    </p>}
                    <p className="mt-1">
                      {item.base}
                    </p>
                  </VetSubCard>

                  <VetSubCard medicine={
                    <Tag className="black my-2" color="#f1b680">
                      {item.continue_medicine ? item.continue_medicine : "持续治疗建议："}
                    </Tag>
                  }>
                    {item.continue_medicine_usage && <p className="mt-1 text-[#f1b680] font-bold text-sm">
                      {item.continue_medicine_usage}
                    </p>}
                    <p className="mt-1">
                      {item.continue}
                    </p>
                  </VetSubCard>

                  <VetSubCard medicine={
                    <Tag color="#dd524c" className="black my-2">
                      {item.suggest_medicine ? item.suggest_medicine : "紧急就诊建议："}
                    </Tag>
                  }>
                    {item.suggest_medicine_usage && <p className="mt-1 text-[#dd524c] font-bold text-sm">
                      {item.suggest_medicine_usage}
                    </p>}
                    <p className="mt-1">
                      {item.suggest}
                    </p>
                  </VetSubCard>
                </VetCard>

              )
            })
          }

          {
            doctor === "中医" && herb_data.data.map(item => {
              return (
                <VetCard title="诊断鉴别" key={item.zhengming}>
                  <div className="mt-5 flex items-center justify-start flex-wrap">
                    <span className="text-2xl font-bold mr-2 text-wrap whitespace-break-spaces">{item.zhengming}</span>
                    {item.p >= 0.8 && <Tag color="#f00" className="inline-block">
                      概率极高
                    </Tag>}
                    {item.p >= 0.5 && item.p < 0.8 && <Tag color="#ff9900" className="inline-block">
                      概率较高
                    </Tag>}
                    {item.p < 0.5 && <Tag color="#030" className="inline-block">
                      概率较低
                    </Tag>}
                  </div>
                  <p className="my-3">
                    {item.therapy && <Tag color="#ff9900" className="inline-block">
                      {item.therapy}
                    </Tag>}
                    {`${item.description}。`}
                  </p>

                  <VetSubCard medicine={
                    <Tag className="black my-2" color="#8093f3">
                      {"初步治疗建议："}
                    </Tag>
                  }>
                    {item.base_prescription && <p className="mt-1 text-[#8093f3] font-bold text-sm">
                      {item.base_prescription}
                    </p>}
                    {item.base_prescription_usage && <p className="mt-1 text-[#8093f3] font-bold text-sm">
                      {item.base_prescription_usage}
                    </p>}
                    <p className="mt-1">
                      {item.base}
                    </p>
                  </VetSubCard>

                  <VetSubCard medicine={
                    <Tag className="black my-2" color="#f1b680">
                      {"持续治疗建议："}
                    </Tag>
                  }>
                    {item.continue_prescription && <p className="mt-1 text-[#f1b680] font-bold text-sm">
                      {item.continue_prescription}
                    </p>}
                    {item.continue_prescription_usage && <p className="mt-1 text-[#f1b680] font-bold text-sm">
                      {item.continue_prescription_usage}
                    </p>}
                    <p className="mt-1">
                      {item.continue}
                    </p>
                  </VetSubCard>

                  <VetSubCard medicine={
                    <Tag color="#dd524c" className="black my-2">
                      {item.suggest_medicine ? item.suggest_medicine : "紧急就诊建议："}
                    </Tag>
                  }>
                    {item.suggest_prescription && <p className="mt-1 text-[#dd524c] font-bold text-sm">
                      {item.suggest_prescription}
                    </p>}
                    {item.suggest_prescription_usage && <p className="mt-1 text-[#dd524c] font-bold text-sm">
                      {item.suggest_prescription_usage}
                    </p>}
                    <p className="mt-1">
                      {item.suggest}
                    </p>
                  </VetSubCard>
                </VetCard>

              )
            })
          }
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

const mock_data = {
  "message": "诊断成功",
  "data": [
    {
      "disease": "犬瘟热",
      "description": "出现精神沉郁、食欲废绝、脓性鼻液和眼分泌物增多及腹泻等典型全身症状",
      "p": 0.7,
      "base": "保持环境温暖干燥，提供充足饮水与易消化食物如白粥鸡胸肉；每日用温水清洁眼周及鼻部脓性分泌物；限制剧烈运动并隔离其他犬只避免交叉感染",
      "continue": "若24小时内精神状态改善可逐步恢复原有饮食并观察体温变化；持续监测排便形态与频率记录异常情况；每日测量肛温早晚各一次维持记录以便后续就医参考",
      "suggest": "[紧急]出现持续高热超过39.5℃、[紧急]抽搐或神经症状、[紧急]血便或呕血、[紧急]完全拒食超过48小时需立即前往具备传染病收治资质的动物医院做PCR确诊并进行静脉补液抗病毒治疗",
      "base_medicine": "",
      "base_medicine_usage": "",
      "continue_medicine": "",
      "continue_medicine_usage": "",
      "suggest_medicine": "干扰素注射液+头孢曲松钠+补液盐",
      "suggest_medicine_usage": "由执业兽医按体重计算剂量进行皮下或静脉给药禁止自行使用"
    },
    {
      "disease": "细菌性呼吸道感染继发胃肠炎",
      "description": "浓鼻涕与喷嚏提示上呼吸道细菌感染,腹泻可能为毒素或继发肠道菌群失衡所致",
      "p": 0.25,
      "base": "保持空气流通但避免直吹冷风,喂食低脂易消化食物例如南瓜泥配少量狗粮分多次少量给予;可用生理盐水雾化帮助缓解鼻塞每次10分钟每日2次",
      "continue": "若3天内鼻涕转清食欲恢复可逐渐恢复正常饮食;继续补充益生菌调理肠胃连续使用7天巩固效果;每周称重确保无持续体重下降",
      "suggest": "[需就诊]若出现黄绿色恶臭鼻涕带血、[需就诊]咳嗽加重呈湿咳伴呼吸困难、[需就诊]腹泻转为水样带黏液血丝其中任一情况需在12小时内前往动物医院接受血常规及X光检查以排除肺炎",
      "base_medicine": "",
      "base_medicine_usage": "",
      "continue_medicine": "",
      "continue_medicine_usage": "",
      "suggest_medicine": "速诺片(阿莫西林克拉维酸钾)+蒙脱石散",
      "suggest_medicin e_usage": "剂量必须由兽医根据体重确定严禁自行购买人用抗生素"
    }
  ],
  "code": 200
}

const herb_data = {
  "message": "诊断成功",
  "data": [
    {
      "zhengming": "外感风热夹湿",
      "description": "精神不振为邪伤正气；食欲不振为脾胃受困；浓鼻液与眼屎属热毒壅滞肺窍；打喷嚏乃风邪袭表；拉稀为湿热下注大肠",
      "p": 0.85,
      "therapy": "疏风清热化湿",
      "base": "保持环境温暖干燥避免风寒直吹给予易消化温热食物如小米粥南瓜泥多饮温水",
      "continue": "每日监测体温观察粪便性状变化记录食欲和精神状态若出现高热或便血及时复诊",
      "suggest": "若持续高热不退抽搐或严重脱水应立即送医中西医结合治疗必要时输液支持",
      "base_prescription": "银翘散加减（金银花连翘薄荷桔梗竹叶荆芥牛蒡子甘草芦根）加藿香佩兰以化湿浊可酌加炒白术健脾止泻",
      "base_prescription_usage": "水煎两次混合药液分早晚两次温服每日一剂连用三日",
      "continue_prescription": "若湿热偏重改用三仁汤合葛根芩连汤加减（杏仁白蔻仁薏苡仁葛根黄芩黄连甘草）酌减辛散发汗药防耗气伤津",
      "continue_prescription_usage": "同上煎服法视大便转稠后减半量再服两日巩固疗效",
      "suggest_prescription": "清瘟败毒饮加大黄厚朴通腑泄热急下存阴配合西药抗生素及补液支持疗法由执业兽医操作",
      "suggest_prescription_usage": "病情危急时先灌肠给药后以少量频喂方式服药密切监护电解质平衡中西药间隔一小时以上",
      "disease": "缺失的disease字段",
      "base_medicine": "",
      "base_medicine_usage": "",
      "continue_medicine": "",
      "continue_medicine_usage": "",
      "suggest_medicine": "",
      "suggest_medicine_usage": ""
    }
  ],
  "code": 200
}