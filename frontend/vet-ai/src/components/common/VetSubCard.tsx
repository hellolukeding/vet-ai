import { HealthiconsMedicines24px } from "../icons";

interface VetSubCardProps {
    children?: React.ReactNode;
    medicine: string;
}

const VetSubCard: React.FC<VetSubCardProps> = (props) => {
    return (
        <section className="w-full bg-[#f4f6fe] rounded-lg p-2 mt-2">
            <h3 className="">
                <HealthiconsMedicines24px className="inline-block mr-2 text-2xl text-[#8093f3]" />
                {props.medicine}
            </h3>


            {props.children}
        </section>
    );
};

export default VetSubCard;
